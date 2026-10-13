# Snowset arrival-data acquisition

The [publisher repository](https://github.com/resource-disaggregation/snowset)
accompanies the NSDI 2020 paper *Building An Elastic Query Engine on Disaggregated
Storage*. It describes roughly 70 million Snowflake queries over 14 days. The
[schema](https://github.com/resource-disaggregation/snowset/blob/master/schema.md)
defines `createdTime` as UTC query entry time and `warehouseId` as the anonymized
warehouse identity. This is a database-arrival candidate, unlike cluster CPU usage.

Live HTTPS HEAD verified the [publisher-linked Parquet archive](https://www.cs.cornell.edu/~midhul/snowset/snowset-main.parquet.tar.gz)
at 8,202,394,513 bytes, Last-Modified Sun, 23 Feb 2020 19:00:06 GMT. The CSV alternative
is 7,574,674,365 bytes. Parquet was selected for column-projected inspection of arrival
time/warehouse identity rather than parsing every query metric. Local disk has over
1 TiB available and DuckDB is installed; complete archive and actual schema have now passed validation (see status below).

Preregistered acquisition config: `experiment_protocols/snowset_acquisition_20261014.json`.
The tool creates an exclusive directory, copies config/code, verifies HEAD/GET size
and modification, preserves partial bytes on error, and records actual bytes/SHA256.
No automatic retry, generated substitute, existing-file overwrite or model promotion.
Source raw bytes and progress stay in `datasets/snowset/acquisition_20261014/`.
Do not commit the large archive to GitHub. A complete-byte/hash fallback mirror is retained separately from source acceptance; the old handover-archive publication authorization remains outstanding.

## Evidence gates before use

1. Complete exact-byte download and self-measured SHA256. HTTPS/publisher endpoint
   provenance is available, but no independently published cryptographic checksum.
2. Gzip/tar integrity and safe member inventory; never execute archive contents.
3. Actual Parquet schema/row counts/nulls/unique-query IDs/timestamp ranges and units.
   Inspect warehouse coverage and missingness. Do not assume every warehouse has
   full 14-day coverage or that global cloud demand fits one local server.
4. Select warehouses/time windows using training-only rules; preserve original time,
   query identities and offered arrival timing. No time compression or quiet-tail padding.
5. Preregister training/calibration/test and benchmark mapping. SQL text is absent.
   Completed-query durations/resource/operator profiles are retrospective; using them
   as features before query arrival or to select test windows would leak future data.
6. Keep arrival forecasting evaluation distinct from physical scheduling evaluation.
   A trace forecast alone does not validate Iceberg compaction timing or the cost models.

The [publisher usage statement](https://github.com/resource-disaggregation/snowset/blob/master/README.md)
permits research/education use and requests citation of its NSDI paper. Acquisition
is resource preparation, not an accepted replay/forecast result or novelty claim.

## Validated source and next cohort gate

Corrected full-source validator passed: 2,000 regular Parquet files, **69,182,074 rows
and unique query IDs**, 2,051 warehouses, no missing query/warehouse/arrival IDs,
gzip/tar integrity and stable extracted-file hashes. Actual observed UTC arrivals
span 2018-02-21 20:00:00.286 through 2018-03-07 04:11:22.719. Do not label that
range as fourteen complete days or extend its quiet tail. Original failed reader
run (directory-plus-files duplicated input) remains preserved; no deduplication was
used for acceptance. Evidence: `snowset_complete_source_validation_2026-10-14.json`.

The self-hashed 8,202,394,513-byte archive is identical on local and worker3. Primary
publisher cryptographic authenticity and missing historical recovered-range receipts
remain explicit limitations. Archive bytes are outside GitHub.

Registered `snowset_arrival_cohort_20261014.json` selects a warehouse by training-only
arrival count over the first seven observed days, reserving three subsequent days
and the remaining complete bins. These are diagnostic chronology choices, not an
accepted publication precision protocol. Selection never uses completed-query
resource profiles, held-out volume or forecast accuracy. Exact arrivals are retained;
one-minute counts use only complete global-source bins. Empty bins mean no reported
arrivals, not proven server idle time. The resulting offered rate may exceed worker3
capacity; no scaling/thinning/time compression is authorized. SQL mapping and valid
physical training/evaluation remain separate gates.
