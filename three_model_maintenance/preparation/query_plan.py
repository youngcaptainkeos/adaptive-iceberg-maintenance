"""Extract counted operators from actual pre-execution Spark FORMATTED plans.

No SQL-length complexity score, optimizer-cost/runtime conversion, or imputed
cardinality. Raw COST statistics remain explicitly unvalidated observations.
"""
import hashlib
import re
from collections import Counter
from pathlib import Path
from three_model_maintenance.contracts import require

CATEGORIES={
 'scan':{'BatchScan','FileScan','Scan','LocalTableScan','ExistingRDD','RowDataSourceScan'},
 'join':{'BroadcastHashJoin','SortMergeJoin','ShuffledHashJoin','BroadcastNestedLoopJoin','CartesianProduct'},
 'aggregate':{'HashAggregate','SortAggregate','ObjectHashAggregate'},
 'exchange':{'Exchange','BroadcastExchange','ShuffleExchange','ReusedExchange'},
 'sort':{'Sort','TakeOrderedAndProject'},'filter':{'Filter'},'window':{'Window'}}


def parse(formatted,cost):
    require('== Physical Plan ==' in formatted,'Missing real physical plan')
    headers=re.findall(r'^\((\d+)\)\s+([^\n]+)$',formatted,re.MULTILINE)
    require(headers and len({n for n,_ in headers})==len(headers),'Missing/duplicate physical operator details')
    outline=formatted.split('== Physical Plan ==',1)[1].split('\n\n',1)[0]
    refs=set(re.findall(r'\((\d+)\)',outline))
    require(refs and refs<=set(n for n,_ in headers),'Unparsed outline operator')
    operators=Counter(line.split()[0] for _,line in headers)
    features={'plan_operator_count':len(headers)}
    for name,names in CATEGORIES.items():features['plan_'+name+'_count']=sum(v for op,v in operators.items() if op in names)
    require(features['plan_scan_count']>0,'No supported real table-scan operator; preserve raw plan and stop admission')
    require('== Optimized Logical Plan ==' in cost and '== Physical Plan ==' in cost,'Missing real COST plan')
    return {'schema_version':'spark_preexecution_plan_features_v1','features':features,'operators':dict(operators),
            'node_ids':[n for n,_ in headers], 'raw_statistics':re.findall(r'Statistics\([^\n]*',cost),
            'estimated_rows':None,'estimated_bytes':None,
            'statistics_status':'raw_only_missing_or_unvalidated_not_predictors',
            'formatted_sha256':hashlib.sha256(formatted.encode()).hexdigest(),
            'cost_sha256':hashlib.sha256(cost.encode()).hexdigest(),
            'limitations':['Operator counts describe plan structure, not calibrated runtime complexity.',
                           'COST estimates may be missing/default; no numeric conversion or imputation.',
                           'This is the initial pre-execution plan, not retrospective AQE/task statistics.']}
