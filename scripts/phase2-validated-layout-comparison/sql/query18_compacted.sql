select
    c_name,
    c_custkey,
    o_orderkey,
    o_orderdate,
    o_totalprice,
    sum(l_quantity)
from
    local.tpch.customer,
    local.tpch.orders,
    local.experiment.lineitem_validated_compacted
where
    o_orderkey in (
        select
            l_orderkey
        from
            local.experiment.lineitem_validated_compacted
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
limit 100;
