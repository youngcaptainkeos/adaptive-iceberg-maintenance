import os
import yaml
import csv

# Base directory for the experiment
BASE_DIR = "scripts/phase2-validated-layout-comparison"

# SQL Query templates with placeholders
QUERIES = {
    "query1": """SELECT
    l_returnflag,
    l_linestatus,
    sum(l_quantity) as sum_qty,
    sum(l_extendedprice) as sum_base_price,
    sum(l_extendedprice * (1 - l_discount)) as sum_disc_price,
    sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)) as sum_charge,
    avg(l_quantity) as avg_qty,
    avg(l_extendedprice) as avg_price,
    avg(l_discount) as avg_disc,
    count(*) as count_order
FROM
    {lineitem}
WHERE
    l_shipdate <= date '1998-12-01' - interval '90' day
GROUP BY
    l_returnflag,
    l_linestatus
ORDER BY
    l_returnflag,
    l_linestatus;""",

    "query3": """SELECT
    l_orderkey, sum(l_extendedprice*(1-l_discount)) as revenue, o_orderdate, o_shippriority
FROM
    {customer},
    {orders},
    {lineitem}
WHERE
    c_mktsegment = 'BUILDING'
    and c_custkey = o_custkey
    and l_orderkey = o_orderkey
    and o_orderdate < date '1995-03-15'
    and l_shipdate > date '1995-03-15'
GROUP BY
    l_orderkey,
    o_orderdate,
    o_shippriority
ORDER BY
    revenue DESC,
    o_orderdate
LIMIT 10;""",

    "query6": """select
    sum(l_extendedprice * l_discount) as revenue
from {lineitem}
where
    l_shipdate >= date '1994-01-01'
    and l_shipdate < date '1994-01-01' + interval '1' year
    and l_discount between 0.06 - 0.01 and 0.06 + 0.01
    and l_quantity < 24;""",

    "query12": """SELECT
    l_shipmode,
    sum(case
        when o_orderpriority ='1-URGENT'
        or o_orderpriority ='2-HIGH'
        then 1
        else 0
    end) as high_line_count,
    sum(case
        when o_orderpriority <> '1-URGENT'
        and o_orderpriority <> '2-HIGH'
        then 1
        else 0
    end) as low_line_count
FROM
    {orders},
    {lineitem}
WHERE
    o_orderkey = l_orderkey
    and l_shipmode in ('MAIL', 'SHIP')
    and l_commitdate < l_receiptdate
    and l_shipdate < l_commitdate
    and l_receiptdate >= date '1994-01-01'
    and l_receiptdate < date '1994-01-01' + interval '1' year
GROUP BY
    l_shipmode
ORDER BY
    l_shipmode;""",

    "query14": """select
    100.00 * sum(case
        when p_type like 'PROMO%'
        then l_extendedprice*(1-l_discount)
        else 0
    end) / sum(l_extendedprice * (1 - l_discount)) as promo_revenue
from
    {lineitem},
    {part}
where
    l_partkey = p_partkey
    and l_shipdate >= date '1995-09-01'
    and l_shipdate < date '1995-09-01' + interval '1' month;""",

    "query18": """select
    c_name,
    c_custkey,
    o_orderkey,
    o_orderdate,
    o_totalprice,
    sum(l_quantity)
from
    {customer},
    {orders},
    {lineitem}
where
    o_orderkey in (
        select
            l_orderkey
        from
            {lineitem}
        group by
            l_orderkey having
                sum(l_quantity) > 300
    )
    and c_custkey = o_custkey
    and o_orderkey = l_orderkey
group by
    c_name,
    c_custkey,
    o_orderkey,
    o_orderdate,
    o_totalprice
order by
    o_totalprice desc,
    o_orderdate
limit 100;"""
}

# The 6 permutations of the 3 states
PERMUTATIONS = [
    ["control", "fragmented", "compacted"],  # ABC
    ["control", "compacted", "fragmented"],  # ACB
    ["fragmented", "control", "compacted"],  # BAC
    ["fragmented", "compacted", "control"],  # BCA
    ["compacted", "control", "fragmented"],  # CAB
    ["compacted", "fragmented", "control"]   # CBA
]

def main():
    print("Generating SQL query files...")
    sql_dir = os.path.join(BASE_DIR, "sql")
    os.makedirs(sql_dir, exist_ok=True)
    
    # State table mapping
    state_tables = {
        "control": {
            "lineitem": "local.tpch.lineitem",
            "customer": "local.tpch.customer",
            "orders": "local.tpch.orders",
            "part": "local.tpch.part"
        },
        "fragmented": {
            "lineitem": "local.experiment.lineitem_validated_fragmented",
            "customer": "local.tpch.customer",
            "orders": "local.tpch.orders",
            "part": "local.tpch.part"
        },
        "compacted": {
            "lineitem": "local.experiment.lineitem_validated_compacted",
            "customer": "local.tpch.customer",
            "orders": "local.tpch.orders",
            "part": "local.tpch.part"
        }
    }
    
    for q_name, q_template in QUERIES.items():
        for state, mappings in state_tables.items():
            sql_content = q_template.format(
                lineitem=mappings["lineitem"],
                customer=mappings["customer"],
                orders=mappings["orders"],
                part=mappings["part"]
            )
            file_path = os.path.join(sql_dir, f"{q_name}_{state}.sql")
            with open(file_path, "w") as f:
                f.write(sql_content + "\n")
            # print(f"  Wrote {file_path}")
            
    print("Generating LST-Bench configuration files...")
    config_dir = os.path.join(BASE_DIR, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # 1. library.yaml
    library = {
        "version": 1,
        "task_templates": []
    }
    
    queries_list = ["query1", "query3", "query6", "query12", "query14", "query18"]
    for q in queries_list:
        for state in ["control", "fragmented", "compacted"]:
            library["task_templates"].append({
                "id": f"{q}_{state}_task",
                "files": [f"../scripts/phase2-validated-layout-comparison/sql/{q}_{state}.sql"]
            })
            
    with open(os.path.join(config_dir, "library.yaml"), "w") as f:
        yaml.dump(library, f, sort_keys=False)
    print("  Wrote config/library.yaml")
    
    # 2. workload_validated.yaml
    workload = {
        "version": 1,
        "id": "tpch_validated_comparison_workload",
        "phases": []
    }
    
    execution_order_records = []
    
    # Generate 66 phases (22 repetitions * 3 states per repetition)
    for r in range(22):
        perm_idx = r % 6
        perm = PERMUTATIONS[perm_idx]
        
        # Log the execution order for results
        execution_order_records.append({
            "repetition": r,
            "phase_position_1": perm[0].capitalize(),
            "phase_position_2": perm[1].capitalize(),
            "phase_position_3": perm[2].capitalize()
        })
        
        for pos, state in enumerate(perm):
            phase_id = f"rep{r}_pos{pos}_{state}"
            tasks = []
            for q in queries_list:
                tasks.append({
                    "template_id": f"{q}_{state}_task"
                })
            workload["phases"].append({
                "id": phase_id,
                "sessions": [
                    {
                        "tasks": tasks
                    }
                ]
            })
            
    with open(os.path.join(config_dir, "workload_validated.yaml"), "w") as f:
        yaml.dump(workload, f, sort_keys=False)
    print("  Wrote config/workload_validated.yaml")
    
    # Save the execution order csv immediately during preparation
    results_dir = os.path.join(BASE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    order_csv_path = os.path.join(results_dir, "execution_order.csv")
    
    with open(order_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repetition", "phase_position_1", "phase_position_2", "phase_position_3"])
        writer.writeheader()
        writer.writerows(execution_order_records)
    print(f"  Wrote execution order configuration to {order_csv_path}")

if __name__ == "__main__":
    main()
