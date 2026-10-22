# Actual attempt04 preflight and detached launch

Runtime revision `6b88c99499c001109ab58f04943905613467c9ea` was pushed to GitHub and
worker3 fast-forwarded. All13intended file SHA256 values agreed client/server;
unrelated dirty models/cache/archive retained. No active Main/queue collector at
admission. Parentnohup wrapper1298845/orchestrator1298846 started12:06:23UTC
(17:36IST)22October; physicalwrapper1298966/collector1298967 at12:06:45UTC.
At12:07:14UTC physical collector was alive and had no logged failure. That is a
startup checkpoint, not evidence of passed physical collection or A labels.

## Completed actual checks

- Full actual02package roundtrip:30files37262803bytes, original and working copies
  retained, all source/stage/final SHA manifests equal, files/directories fsynced.
  ManifestSHA `5b3ddf213bc7104fd7f67ba726e51ecf6fb84029c56bdc77059ad25033444d23`.
  Audit12:06:24–12:06:26UTC exit0, resultSHA
  `09fb7aca793589dd04775de1cf037faf73950896f8a446f24d706d33029bd194`.
  This checks actual data transport, not SQL execution or scientific acceptance.
- Pure frontier regression12:06:26–12:06:27UTC exit0: all297actual failed-run
  queries reevaluated, exact7stale refusals preserved; no dummy clock/cursor/SQL.
  ResultSHA `33ec3a72eda25f3412693b951b8f67a762bb45862543cc6b2881e2e7a54fa234`.
- Real arrival mapping and independent mapping audit ended12:06:37/12:06:45UTC
  exit0.1554arrivals from same known day6 development family; not new independence.
  MappingSHA `c7d535633f0304eafa14a57169ac5b1c2abac7c756651d0b2353eddb8c364ff9`.
- Actual physicalregistrationSHA
  `db91364d965294c5e38132d9e03a338daf7f1878125a0424b83122c07e71285b`;
  parent protocolSHA `9c939b912ba109a674590d4951867462ac907e87332057d674b7eca4bd2d630a`.
  Source/raw predictor/telemetry/inventory gates unchanged. No model fitted.

Completed audit receipts and physical registration mirrored; SHA256 agrees.
Initial administrative rsync failed because local nested parent directory was
absent, exit11; creating the parent and copying completed receipts succeeded.
This was a mirror-path failure, not a failed experiment or repeated physical run.
Live raw evidence has not been claimed fully mirrored.

## Code explanation

`observability/evidence_workspace.py`: validate a fresh working path on registered
persistent device, check free-space budget, inventory regular files, reject symlinks
and path overlap. After the producer returns, copy into fresh staging, compare every
file's bytes/SHA, fsync files/directories, rename and compare again. No source/failed/
partial copy is deleted. Its result explicitly excludes scientific acceptance.

`audits/evidence_workspace.py`: binds the real successful02parent/physical receipts,
roundtrips the complete existing package, compares unchanged originals. No SQL,
labels or training are created by the test.

`runtime/collector_bridge.py`: restricts the extra outer lock to event kinds that
mutate queue/unsubmitted/observation state. Other events use base serialization
outside its write/fsync lock. Every record still persists; direct journal state
and ordering stay guarded. Faster collection is a hypothesis, not a measured claim.

`runtime/run_registered_collection.py`: checks frozen source and supporting evidence
hashes; runs archive validation before mapping/SQL; reuses bound candidate02bytes
without rerunning an occupied export. New physical04 is isolated. It exports only
after raw/publication audits. In finally, copies a successful OR failed physical
package only after its subprocess returned. Archive errors preserve working data
and cannot become a successful pipeline; a prior physical failure is retained.
Every stage has its own original-exit-preserving ntfy failure wrapper.

## Paths and next check

On worker3, parent `results/three_model_live_collection_fast_evidence_20261022/`:
`progress.json`, `physical.log`, eventual `result.json`, `candidates/` and
`raw_archive_manifest.json`. Launch `results/three_model_live_collection_fast_evidence_20261022_launch/`:
`pid`, `run.log`, unique `failure_alert.json` on failure.
Working `/home/ccbd/capstone_three_model_evidence/sf1_three_model_publication_20261022_04`;
canonical `results/sf1_three_model_publication_20261022_04` only after producer exits.

Expected terminal check~18:00IST (20–30minutes from17:36). Job survives laptop
loss; existing services retained. ntfy failure and evidence-linked completion
notices enabled, not dummy-tested. No agent-side automatic fitting implied.
Need terminal raw/publication/export pass plus observed complete-historyA/B before
new exploratory training admission. Blocked03fit registration remains unchanged.
One known family never grants independent test/calibration/scheduler authorization.
