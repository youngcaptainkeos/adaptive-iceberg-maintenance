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
1 TiB available and DuckDB is installed; archive contents and schema are not yet inspected.

Preregistered acquisition config: `experiment_protocols/snowset_acquisition_20261014.json`.
The tool creates an exclusive directory, copies config/code, verifies HEAD/GET size
and modification, preserves partial bytes on error, and records actual bytes/SHA256.
No automatic retry, generated substitute, existing-file overwrite or model promotion.
Source raw bytes and progress stay in `datasets/snowset/acquisition_20261014/`.
Do not commit the large archive to GitHub. Mirror only after complete acquisition
and validation; the old handover-archive publication authorization remains outstanding.

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
