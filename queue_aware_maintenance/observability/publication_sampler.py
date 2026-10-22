"""Wake on actual durable telemetry publication; retain all original age/gap gates."""
# Support both package imports and direct worker3 script entry points.
if __package__ in (None, ""):
 import sys as _sys
 from pathlib import Path as _Path
 _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from queue_aware_maintenance.paths import PACKAGE_ROOT, REPOSITORY_ROOT, source_file
import threading,time
from physical_measurements import TelemetrySampler,stamp
from experiment_validation import ValidationError

class PublicationTelemetrySampler(TelemetrySampler):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.available=threading.Condition(self.lock)
 def _publish(self,kind,fields):
  if self.asynchronous_persistence:self.persistence_queue.put((kind,fields))
  else:
   self.log.emit(kind,**fields)
   if kind=='telemetry_interval':
    with self.available:self.samples.append(fields);self.available.notify_all()
 def _persist(self):
  try:
   while True:
    item=self.persistence_queue.get()
    if item is None:return
    kind,fields=item;self.log.emit(kind,**fields)
    if kind=='telemetry_interval':
     # EventLog.emit has flushed/fsynced before this sample becomes observable.
     with self.available:self.samples.append(fields);self.available.notify_all()
  except Exception as exc:
   self.failure=exc;self.log.emit('telemetry_failed',error_type=type(exc).__name__,error=str(exc))
  finally:
   with self.available:self.available.notify_all()
 def wait_for_available_sample(self,*,deadline_ns,max_age_seconds,measurement_id):
  started=stamp();waited=False;initial=None;last=None
  with self.available:
   while time.monotonic_ns()<deadline_ns:
    if self.failure:raise ValidationError(f'Telemetry failed: {self.failure}')
    last=self.samples[-1]['end']['monotonic_ns'] if self.samples else None
    if initial is None:initial=last
    current=time.monotonic_ns()
    if last is not None and 0<=(current-last)/1e9<=max_age_seconds:break
    waited=True;self.available.wait(timeout=max(0,(deadline_ns-current)/1e9))
   else:last=None
  if last is not None:
   if waited:self.log.emit('query_telemetry_availability_wait',measurement_id=measurement_id,started=started,ended=stamp(),initial_available_sample_end_ns=initial,actual_available_sample_end_ns=last,deadline_monotonic_ns=deadline_ns,outcome='actual_fresh_durable_sample_available',wake_contract='durable_publication_condition_v1')
   return True
  self.log.emit('query_telemetry_availability_wait',measurement_id=measurement_id,started=started,ended=stamp(),initial_available_sample_end_ns=initial,deadline_monotonic_ns=deadline_ns,outcome='horizon_reached_request_retained_queued',wake_contract='durable_publication_condition_v1');return False
 def wait_for_publication_after(self,*,sample_end_ns,deadline_ns):
  """Wait for the next actual sample, useful for strict submission preparation."""
  with self.available:
   while time.monotonic_ns()<deadline_ns:
    if self.failure:raise ValidationError(f'Telemetry failed: {self.failure}')
    if self.samples and self.samples[-1]['end']['monotonic_ns']>sample_end_ns:return self.samples[-1]
    self.available.wait(timeout=max(0,(deadline_ns-time.monotonic_ns())/1e9))
  return None
