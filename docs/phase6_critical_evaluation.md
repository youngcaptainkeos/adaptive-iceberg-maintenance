# Phase 6 Results: Harsh Critical Evaluation

> **Verdict: These results are currently UNUSABLE for any publication. They contain multiple fatal flaws that would be caught in the first 30 seconds of peer review.**

---

## The Summary Table You Produced

| Policy | Compactions | Forced Overrides | Override Rate | Avg Query Latency (ms) | SLA Violation Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| SOTAThresholdPolicy (Baseline) | 1 | 0 | 0% | **19,009.9** | **98.57%** |
| TemporalConformalPolicy (Ours) | 35 | 12 | 34.29% | **16,797.7** | **97.18%** |

---

## Fatal Flaw #1: The Entire Experiment Ran in Simulation Mode

> [!CAUTION]
> **PyHive was not connected to a running Spark Thrift Server.** Every single "query" and "compaction" in both Run A and Run B was **simulated** — fake sleep delays, synthetic latency numbers, no actual data was read or rewritten.

**Evidence from the data:**
- Run A: Only **1 compaction** executed in the entire 3,570-second run (and after that, `frag_file_count` dropped from 593 → 32 and **never changed again** for the remaining 70 rows). If real queries were running against a real 15GB table, file counts would fluctuate.
- Run B: After the initial `FORCED_OVERRIDE` compaction at row 5, `frag_file_count` is stuck at **32 for all 67 remaining rows**. No new fragmentation was generated because **no real writes were happening**.
- The `compaction_duration_s` values for "RUN" decisions in Run B are `0.05`, `0.19`, `0.06` seconds. Real Iceberg `rewrite_data_files` on a 15GB table takes **2-10 minutes**, not 50 milliseconds.
- The `avg_query_latency_ms` values are `14,000-19,000ms` (14-19 **seconds**). This is the simulated `WorkloadDriver` accumulating `200 + intensity * 250 + noise` millisecond values and then reporting the **cumulative** average — not per-query latency. The numbers are meaningless.

**Reviewer verdict:** *"The authors did not actually run their system. All reported numbers are from a simulation with hardcoded latency distributions. Reject."*

---

## Fatal Flaw #2: The "avg_query_latency_ms" Column Is Not Query Latency

Look at the CSV values: `135,939ms`, `50,182ms`, `41,005ms`... These are **not** individual query latencies. They are the **running average of cumulative simulated latency across all queries ever executed by the background thread**.

The `WorkloadDriver._record_query_result()` appends to `self.recent_latencies` (capped at 50), and `get_stats()` returns `np.mean(self.recent_latencies)`. But the simulated latency per query is `200 + intensity*250 + noise ≈ 200-450ms`. The reported 14,000-19,000ms values suggest the stat is being accumulated or misreported somehow.

Regardless: **these are not real query execution times from Spark**. No reviewer would accept them.

---

## Fatal Flaw #3: SOTAThresholdPolicy Compacted Once and Then Did Nothing

The baseline policy (`frag_file_threshold=200`) triggered compaction **once** at `t=0` (because 593 > 200), reducing files from 593 → 32. After that, it correctly DEFERed because `32 < 200`. But since no real workload was generating new small files, fragmentation never grew back. So the baseline just sat idle for 56 minutes.

This means **the A/B comparison is meaningless**:
- Baseline: 1 compaction, then idle.
- Our policy: 35 compactions (12 forced), all on an already-compacted table (32 files), doing nothing useful.

**Reviewer verdict:** *"The experimental setup does not generate ongoing fragmentation. The baseline compacts once and achieves optimal state. The proposed system runs 35 unnecessary compactions on an already-healthy table. This is not a valid comparison."*

---

## Fatal Flaw #4: No Ongoing Fragmentation / Write Workload

A real Iceberg lakehouse has **continuous writes** (INSERT, MERGE, DELETE) that create new small data files, driving fragmentation growth over time. Your experiment has:
- ❌ No write workload generating new Parquet files
- ❌ No append stream simulating ETL ingestion
- ❌ No fragmentation growth curve over time

Without ongoing writes, compaction is a one-shot operation with no recurring decision problem. The entire scheduling agent is pointless.

---

## Fatal Flaw #5: Both Policies Show ~98% SLA Violation Rate

| Policy | SLA Violation Rate |
| :--- | :---: |
| Baseline | 98.57% |
| Ours | 97.18% |

**Both policies violate the SLA on nearly every query.** This is supposed to be the headline result proving our agent works. Instead, it proves the opposite. A 1.4 percentage-point difference in SLA violation rate is:
1. Statistically insignificant (no confidence intervals computed).
2. Not practically meaningful (both are catastrophically bad).
3. Likely an artifact of simulation noise.

**Reviewer verdict:** *"The proposed system achieves 97% SLA violation rate versus the baseline's 98%. This is not a meaningful improvement."*

---

## Fatal Flaw #6: Duration Was ~1 Hour, Not 8 Hours

The `--duration-hours` default is 8.0, but both runs lasted approximately **3,570 seconds ≈ 59.5 minutes ≈ 1 hour**. The Google Borg trace diurnal curve was compressed into 1 hour instead of 8, meaning the workload intensity cycling was 8x faster than intended. This invalidates the trace-driven evaluation claim.

---

## Fatal Flaw #7: 34% Forced Override Rate

Our `TemporalConformalPolicy` triggered **`FORCED_OVERRIDE` 12 out of 35 times (34.3%)**. This means the conformal prediction framework was overridden by the safety mechanism more than a third of the time. From a reviewer's perspective:

*"The conformal prediction component is bypassed 34% of the time by a simple counter-based safety valve. What is the value of the statistical framework if it cannot make decisions on its own?"*

---

## What Actually Needs to Happen

### Step 1: Run Against a Real Spark Thrift Server
- Start the Spark Thrift Server on `worker3` with Iceberg catalog pointing to `warehouse/tpch_sf100`.
- Verify PyHive can connect and execute `SELECT count(*) FROM local.tpch_sf100.lineitem`.
- Verify `CALL local.system.rewrite_data_files(table => 'local.tpch_sf100.lineitem')` executes and returns real metrics.

### Step 2: Add a Write Workload (Critical Missing Piece)
The experiment **must** include a continuous write stream that generates new small files over time. For example:
```sql
-- Every 30-60 seconds, insert a batch of rows to create new small Parquet files
INSERT INTO local.tpch_sf100.lineitem
SELECT * FROM local.tpch_sf100.lineitem
WHERE L_ORDERKEY BETWEEN <random_start> AND <random_start + 1000>
```
This creates ongoing fragmentation growth, giving the scheduling agent a real recurring decision problem.

### Step 3: Fix the Metrics
- Report **per-query p50/p95/p99 latency** (not running averages).
- Report **fragmentation trajectory over time** (file count at each decision point, which should grow between compactions).
- Report **query latency during vs. outside compaction windows** (this is the core interference measurement).

### Step 4: Run for the Full 8 Hours
- Use `--duration-hours 8` with the Spark Thrift Server actually running.
- The GoogleTraceMapper diurnal cycle needs to play out over the full duration.

### Step 5: Reset Table State Between Runs
- Before Run B, the table must be restored to the exact same initial fragmentation state as Run A started with (593 files, 15.8GB).

---

## Bottom Line

The code infrastructure you built (WorkloadDriver, GoogleTraceMapper, ConsecutiveDeferralTracker, CSV logging) is **good scaffolding**. But the experiment ran in simulation mode against a table that wasn't being written to, producing numbers that are meaningless. 

The path forward is clear:
1. Get Spark Thrift Server running on `worker3` with Iceberg.
2. Add a write workload that continuously fragments the table.
3. Re-run both policies against the **real** system for 8 hours.
4. Report real Spark query execution latencies.

Without these fixes, this data cannot appear in any paper.
