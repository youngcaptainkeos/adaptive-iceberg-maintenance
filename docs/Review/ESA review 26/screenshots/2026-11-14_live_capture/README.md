# ESA review evidence — 14 November 2026

## LIVE Spark UI screenshot

20261114T045129Z_LIVE_SPARK_UI.png was captured through the actual SSH-forwarded Spark UI at approximately10:21am IST. The image visibly shows one active job,3124, for the customer/orders/lineitem query; the separate nearby REST snapshot recorded two active jobs. These are different instants, not inconsistent fabricated counts. Completed jobs below include earlier historical jobs:3126 is not the number of queries run today. See the timestamped manifest and running_jobs.json. This screenshot is historical after capture.

## Historical results dashboard

HISTORICAL_RESULTS_AND_NEXT_GATE.png displays the six real service-time/task-CPU observations, the preserved5/1/0 integration outcome, the passed24-stage/168-task count diagnostic and the remaining comparison gate. baseline_source.json is the actual worker3 export, with SHA256 in results_capture_manifest.json. CPU seconds sum parallel task CPU and must not be described as elapsed time or server-wide CPU. One observation per query cannot establish improvement or statistical significance.

## Storage

The original Data1 project drive was unavailable. These new screenshots are saved here rather than overwriting the earlier ESA folder. A reviewable copy is also kept in the temporary repository checkout under docs/Review/ESA review26/screenshots/2026-11-14_live_capture (the actual folder name contains spaces). Earlier screenshots on Data1 have not been deleted. HTML pages are readable evidence displays, not synthetic terminal sessions.
