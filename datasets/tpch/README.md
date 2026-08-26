# TPC-H Dataset Preparation

This directory contains the TPC-H data generation tools and the generated Scale Factor 1 (SF1) dataset for the "Lakehouse Storage Maintenance Scheduler" project.

## 1. Source of TPC-H Tools

The TPC-H Benchmark Tool (V3.0.1) was already extracted inside the workspace at:
`datasets/tpch/TPC-H-Tool/TPC-H V3.0.1/`

## 2. Tool Compilation (`dbgen` and `qgen`)

To build the tools on Linux, we configured `makefile` within `datasets/tpch/TPC-H-Tool/TPC-H V3.0.1/dbgen/` to use `gcc`, the target database system `SQLSERVER`, and the platform `LINUX`:

```makefile
CC      = gcc
DATABASE= SQLSERVER
MACHINE = LINUX
WORKLOAD = TPCH
```

Then compiled it by executing:
```bash
cd "datasets/tpch/TPC-H-Tool/TPC-H V3.0.1/dbgen"
make
```

This built the `dbgen` (data generator) and `qgen` (query generator) executables locally.

## 3. Data Generation

We generated the Scale Factor 1 (SF1) dataset using the compiled `dbgen` tool:
```bash
cd "datasets/tpch/TPC-H-Tool/TPC-H V3.0.1/dbgen"
./dbgen -vf -s 1
```

The resulting `.tbl` flat files were moved to their permanent location under:
`datasets/tpch/sf1/`

## 4. Verification & Validation

The generated tables were validated by counting their rows and calculating their sizes and SHA256 checksums. The row counts match the standard TPC-H SF1 cardinalities exactly:

| Table Name | Row Count | File Size (Bytes) | SHA256 Checksum |
|---|---|---|---|
| `customer.tbl` | 150,000 | 24,346,144 | `4483680548a965833877c911ed43e795f4d3543c7a3f7d1dba9ccb24ea5989d6` |
| `lineitem.tbl` | 6,001,215 | 759,863,287 | `96d555e07a1ae8cf5196387d9edd9427f9af70c56fa5f4b18affee5555ddb184` |
| `nation.tbl` | 25 | 2,224 | `66f96949939fa8fdf1c4ffed1e5f6c2842fe11a14b51fdc6ed1e17460031e8c5` |
| `orders.tbl` | 1,500,000 | 171,952,161 | `8709061d7bbc81932356fdfc664f8d582252747c2d7e204ae6d3cde624586357` |
| `part.tbl` | 200,000 | 24,135,125 | `f0e4ccdfb5f6d19428ce54f9c84b17037d20f00ac8d2b2272c8d43b18a0b4880` |
| `partsupp.tbl` | 800,000 | 118,984,616 | `43c37f99918f06d4de6b99b05c0a28d5c46f71d66424cffcc595cb059a499254` |
| `region.tbl` | 5 | 389 | `6022658d673924389b54dcb70fa8c3d6da1b0d7afa3c1c017bab62a019df404f` |
| `supplier.tbl` | 10,000 | 1,409,184 | `9b99cf155974e6db8773970b40746bfccfa64fa078169574165f3e19e2158391` |

## 5. How to Regenerate SF1

To regenerate the dataset, run:
```bash
cd "datasets/tpch/TPC-H-Tool/TPC-H V3.0.1/dbgen"
make clean && make
./dbgen -vf -s 1
mkdir -p "../../sf1"
mv *.tbl "../../sf1/"
```
