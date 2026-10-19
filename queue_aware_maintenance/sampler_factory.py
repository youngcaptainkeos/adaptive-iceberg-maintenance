"""Explicit future observer selection; old episode protocols retain old observer."""
import json
from pathlib import Path
from common import checked,require,sha
from physical_measurements import TelemetrySampler
from publication_sampler import PublicationTelemetrySampler

def build_sampler(cfg,log):
 version=cfg.get('telemetry_wait_contract','interval_poll_v1');require(version in ('interval_poll_v1','durable_publication_v2'),'Unknown registered telemetry wait contract')
 if version=='durable_publication_v2':
  validation=checked(cfg['telemetry_publication_validation']);proof=json.loads(validation.read_text());audit=json.loads(checked(cfg['telemetry_publication_audit']).read_text())
  require(proof['status']=='passed_real_durable_publication_and_original_window_gates' and audit['status']=='passed_independent_real_publication_window_reconstruction','Observer validation/audit not passed')
  require(audit['validation_sha256']==sha(validation) and proof['sampler_sha256']==audit['sampler_sha256']==sha(Path(__file__).parent/'publication_sampler.py'),'Observer proof/source binding differs')
  for key in ('interval_seconds','window_seconds','warmup_seconds','max_interval_seconds','max_age_seconds','minimum_coverage_fraction'):require(cfg['telemetry'][key]==audit['telemetry'][key],'Observer numerical gates changed after validation')
  require(cfg['telemetry']['interval_seconds']==audit['submission_max_age_seconds'],'Submission freshness differs')
  cls=PublicationTelemetrySampler
 else:cls=TelemetrySampler
 return cls(log,cfg['telemetry']['interval_seconds'],asynchronous_persistence=True)
