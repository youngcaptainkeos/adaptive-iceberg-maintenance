"""Actual full-cohort FIFO ledger, including dispatches during queue drain."""
import threading
from common import require
from physical_measurements import stamp

class CohortLedger:
 def __init__(self,log,arrivals,start_ns):
  self.log=log;self.arrivals={r['source_query_id']:r for r in arrivals};self.order=[r['source_query_id'] for r in arrivals];self.start_ns=start_ns;self.states={};self.identities={};self.lock=log.lock;self.active=None;self.last_offered_query_id=None
 def transition(self,row,state,mid):
  identity=row['source_query_id']
  with self.lock:
   previous=self.states.get(identity);require(self.arrivals.get(identity)==row,'Unknown/changed physical source')
   require((previous,state) in [(None,'offered'),('offered','queued'),('queued','dispatched'),('dispatched','completed'),('dispatched','failed')],'Invalid physical queue edge')
   if state=='offered':self.identities[identity]=mid;self.last_offered_query_id=int(row['query_id'])
   require(self.identities[identity]==mid,'Changed physical measurement identity')
   if state=='dispatched':require(self.active is None,'Busy serial client');self.active=identity
   if state in ('completed','failed'):require(self.active==identity,'Wrong active query');self.active=None
   event=self.log.emit('cohort_queue_transition',source=row,state=state,previous_state=previous,measurement_id=mid,scheduled_monotonic_ns=self.start_ns+int(row['offset_ns']),actual_transition=stamp());self.states[identity]=state;return event
 def queued(self):
  with self.lock:return [self.arrivals[i] for i in self.order if self.states.get(i)=='queued']
 def census(self,kind):
  from collections import Counter
  with self.lock:return self.log.emit(kind,states=dict(self.states),counts=dict(Counter(self.states.values())),active_source_query_id=self.active)
