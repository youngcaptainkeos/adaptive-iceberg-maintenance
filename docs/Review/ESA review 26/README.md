# ESA review 26 evidence

Screenshots are captured automatically from real worker3 pages. Filenames include UTC capture time, campaign ID, and LIVE/HISTORICAL/MIXED scope. Each group includes a source JSON snapshot; capture_manifest.jsonl records source URL, observation time, capture exit status and image SHA256. Browser logs are retained.

- LIVE_processes: current remote process listing; an idle Spark service is not an active experiment.
- LIVE_Spark_UI_historical_jobs: live Spark UI; its completed jobs may be historical.
- MIXED_live_service_historical_results: current service state alongside explicitly labelled saved results.
- HISTORICAL_failed_audit: original failed campaign status, never a pass certificate.

The first session uses protocols/esa_review_recovery_20261111.json. Browser capture requires the laptop and SSH tunnel; real server-side science is detached and survives laptop disconnection. Saved pages and screenshots remain historical after capture. Missing evidence stays unknown. No screenshots are generated to imply experiments are running when they are not.
