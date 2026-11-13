"""Bounded design enumeration. Rows are plans, never observations or launch authority."""
import itertools
import math
import random
from collections import defaultdict
from .common import integer, number, require, utc


def validate_program(program):
    require(program['schema'] == 'capstone_research_program_v1', 'Unknown research programme')
    require(program['status'] == 'prospective_not_physical_registration', 'Cannot promote programme')
    require(program['primary_metric'] == 'full_cohort_mean_response_seconds', 'Primary objective changed')
    by_id = {e['id']: e for e in program['experiments']}
    require(len(by_id) == len(program['experiments']) > 0, 'Duplicate/absent experiments')
    done, visiting = set(), set()
    def visit(eid):
        require(eid in by_id and eid not in visiting, 'Unknown prerequisite or cycle: ' + eid)
        if eid in done:
            return
        visiting.add(eid)
        e = by_id[eid]
        for field in ('question', 'intervention', 'held_fixed', 'evidence', 'continue_if', 'stop_if'):
            require(isinstance(e[field], str) and e[field].strip(), f'{eid}: missing {field}')
        require(e['state'] == 'planned', 'Plans cannot record an invented completion')
        for dep in e['requires']:
            visit(dep)
        visiting.remove(eid)
        done.add(eid)
    for eid in by_id:
        visit(eid)
    for name, stage in program['designs'].items():
        require(stage['experiment_id'] in by_id, 'Unknown design experiment')
        integer(stage['order_seed'], 'order seed')
        require(stage['factors'], 'Empty design')
        for key, levels in stage['factors'].items():
            require(isinstance(levels, list) and levels and len(set(map(str, levels))) == len(levels),
                    f'{name}/{key}: missing or duplicate levels')
        require(stage['rationale'].strip(), 'Design parameters require rationale')
    return program


def enumerate_design(program, name, blocks, max_units=10000):
    """Complete Cartesian product ONLY within one registered small design.

    Shuffled base order is rotated across blocks. This balances position when the
    block count is a multiple of arm count; it does not prove absence of drift.
    Block labels are prospective slots, not claims of independent source families.
    """
    validate_program(program)
    integer(blocks, 'block slots', 1)
    integer(max_units, 'maximum units', 1)
    stage = program['designs'][name]
    keys = list(stage['factors'])
    count = math.prod(len(stage['factors'][k]) for k in keys) * blocks
    require(count <= max_units, f'{count} planned units exceed limit {max_units}; narrow the design')
    arms = [dict(zip(keys, values)) for values in itertools.product(*(stage['factors'][k] for k in keys))]
    order = list(range(len(arms)))
    random.Random(stage['order_seed']).shuffle(order)
    rows = []
    for b in range(blocks):
        rotated = order[b % len(arms):] + order[:b % len(arms)]
        for position, arm in enumerate(rotated):
            rows.append({'planned_unit_id': f'{name}_block{b + 1:03d}_arm{arm + 1:03d}',
                         'block_slot': b + 1, 'execution_position': position + 1,
                         'factors': arms[arm], 'source_family': None, 'table_identity': None,
                         'state': 'unbound_plan_not_launched'})
    return {'schema': 'research_design_v1', 'design': name, 'experiment_id': stage['experiment_id'],
            'planned_units': count, 'arms_per_block': len(arms), 'block_slots': blocks,
            'order_seed': stage['order_seed'], 'position_balanced': blocks % len(arms) == 0,
            'physical_execution_authorized': False, 'rows': rows,
            'required_before_physical_registration': program['physical_registration_requirements'],
            'limitations': ['Planning slots are not observed independent blocks.',
                           'No SQL, synthetic observations, outcomes, or prediction values were generated.']}


def budget(program, name, blocks, episode_minutes, setup_minutes):
    """Transparent sensitivity calculation; caller supplies measured estimates."""
    validate_program(program)
    integer(blocks, 'block slots', 1)
    count = math.prod(len(v) for v in program['designs'][name]['factors'].values()) * blocks
    number(episode_minutes, 'measured episode minutes', 0)
    number(setup_minutes, 'measured setup minutes', 0)
    return {'planned_units': count, 'serial_hours':
            count * (episode_minutes + setup_minutes) / 60,
            'episode_minutes_input': episode_minutes, 'setup_minutes_input': setup_minutes,
            'meaning': 'Arithmetic estimate from supplied durations; no completion-time guarantee; excludes failures/recovery'}


def overlap_families(windows):
    """Connected components of actual source ranges, including feature history.

    This is leakage grouping only. Disjoint components can still be temporally
    dependent. Source identity must include dataset and warehouse, not just day.
    """
    require(windows and len({w['id'] for w in windows}) == len(windows), 'Missing/duplicate source windows')
    parents = list(range(len(windows)))
    ranges = []
    for w in windows:
        require(w['dataset_id'] and w['warehouse_id'], 'Source identity missing')
        left, start, right = utc(w['history_start_utc']), utc(w['start_utc']), utc(w['end_utc'])
        require(left <= start < right, 'Source/history bounds reversed')
        ranges.append((left, right))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for i, a in enumerate(windows):
        for j in range(i):
            b = windows[j]
            same = (a['dataset_id'], a['warehouse_id']) == (b['dataset_id'], b['warehouse_id'])
            if same and max(ranges[i][0], ranges[j][0]) < min(ranges[i][1], ranges[j][1]):
                parents[find(i)] = find(j)
    groups = defaultdict(list)
    for i, w in enumerate(windows):
        groups[find(i)].append(w['id'])
    return {'overlap_components': sorted(sorted(g) for g in groups.values()),
            'independence_established': False,
            'rule': 'Same dataset/warehouse and intersecting half-open history-through-outcome ranges; transitive closure'}
