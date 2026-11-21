"""Original arrival horizon and operational dispatch cutoff are distinct."""
from collections import Counter
from physical_measurements import stamp
from three_model_maintenance.research.common import require


class FullDrainLedger:
    def __init__(self,log,mapped,start_ns,arrival_end_ns,dispatch_end_ns):
        self.log=log;self.lock=log.lock;self.rows={r['source_query_id']:r for r in mapped}
        require(mapped and len(self.rows)==len(mapped),'Empty/duplicate offered population')
        self.start=start_ns;self.arrival_end=arrival_end_ns;self.dispatch_end=dispatch_end_ns
        require(start_ns<arrival_end_ns<dispatch_end_ns,'No registered drain admission time')
        self.states={};self.mids={};self.active=None

    def transition(self,row,state,mid,reason=None):
        with self.lock:
            sid=row['source_query_id'];require(self.rows.get(sid)==row,'Changed source row')
            before=self.states.get(sid);require((before,state) in (
                (None,'offered'),('offered','queued'),('queued','dispatched'),
                ('dispatched','completed'),('dispatched','failed')),'Illegal full-drain transition')
            actual=stamp();due=self.start+int(row['offset_ns'])
            if state=='offered':
                require(actual['monotonic_ns']>=due and mid not in self.mids.values(),'Invalid arrival/identity')
                self.mids[sid]=mid
            require(self.mids[sid]==mid,'Changed call identity')
            if state=='dispatched':
                require(self.active is None and actual['monotonic_ns']<self.dispatch_end,'Busy/cutoff serial dispatch')
                self.active=sid
            if state in ('completed','failed'):
                require(self.active==sid,'Wrong completion slot');self.active=None
            self.log.emit('queue_transition',source=row,state=state,previous_state=before,
                          measurement_id=mid,session_id='query_0' if state in ('dispatched','completed','failed') else None,
                          scheduled_monotonic_ns=due,actual_transition=actual,reason=reason)
            self.states[sid]=state

    def census(self,kind):
        with self.lock:
            return self.log.emit(kind,states=dict(self.states),counts=dict(Counter(self.states.values())),
                                 active_source_id=self.active,arrival_end_monotonic_ns=self.arrival_end,
                                 dispatch_end_monotonic_ns=self.dispatch_end)
