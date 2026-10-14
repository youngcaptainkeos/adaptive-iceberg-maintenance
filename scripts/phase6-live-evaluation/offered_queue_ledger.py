"""Actual queue transitions, never simulated demand or service durations."""
import threading
from collections import Counter
from physical_measurements import stamp
from experiment_validation import require


class OfferedQueueLedger:
    def __init__(self,log,scheduled,start_ns,end_ns):
        self.log=log;self.scheduled={r['source_query_id']:r for r in scheduled}
        require(len(self.scheduled)==len(scheduled),'Duplicate arrivals')
        self.start_ns=start_ns;self.end_ns=end_ns;self.states={};self.slots={};self.lock=threading.Lock()

    def transition(self,identity,state,*,measurement_id,session_id=None):
        with self.lock:
            require(identity in self.scheduled,'Unknown offered source')
            previous=self.states.get(identity)
            require((previous,state) in ((None,'offered'),('offered','queued'),('queued','dispatched'),('dispatched','completed'),('dispatched','failed')),'Illegal queue transition')
            actual=stamp()
            if state=='dispatched':
                require(session_id is not None and session_id not in self.slots and actual['monotonic_ns']<self.end_ns,'Busy session or dispatch beyond horizon')
                self.slots[session_id]=identity
            if state in ('completed','failed'):
                require(self.slots.get(session_id)==identity,'Outcome without its session dispatch');del self.slots[session_id]
            record=self.log.emit('queue_transition',source=self.scheduled[identity],state=state,previous_state=previous,actual_transition=actual,measurement_id=measurement_id,session_id=session_id,scheduled_monotonic_ns=self.start_ns+int(self.scheduled[identity]['offset_ns']))
            self.states[identity]=state
            return record

    def boundary(self):
        with self.lock:
            require(stamp()['monotonic_ns']>=self.end_ns,'Boundary before horizon')
            return self.log.emit('queue_boundary',horizon_start_monotonic_ns=self.start_ns,horizon_end_monotonic_ns=self.end_ns,observed_states=dict(self.states),observed_counts=dict(Counter(self.states.values())),not_yet_offered=[identity for identity in self.scheduled if identity not in self.states],active_sessions=dict(self.slots),meaning='Actual observer state at recorded boundary; observation lateness retained, not silently an exact-time census')
