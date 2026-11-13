"""Research design CLI. Outputs are plans or supplementary analyses, never launches."""
import argparse
from pathlib import Path
from .common import read, write_new
from .design import budget, enumerate_design, overlap_families, validate_program
from .accounting import reconstruct
from .comparison import compare


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('validate-program', 'plan', 'budget'):
        q = sub.add_parser(name)
        q.add_argument('--program', type=Path, required=True)
        q.add_argument('--output', type=Path, required=True)
        if name != 'validate-program':
            q.add_argument('--design', required=True)
            q.add_argument('--blocks', type=int, required=True)
        if name == 'budget':
            q.add_argument('--episode-minutes', type=float, required=True)
            q.add_argument('--setup-minutes', type=float, required=True)
    q = sub.add_parser('overlap-families')
    q.add_argument('--windows', type=Path, required=True)
    q.add_argument('--output', type=Path, required=True)
    q = sub.add_parser('account')
    q.add_argument('--episode', type=Path, required=True)
    q.add_argument('--pins', type=Path, required=True)
    q.add_argument('--output', type=Path, required=True)
    q = sub.add_parser('compare')
    q.add_argument('--manifest', type=Path, required=True)
    q.add_argument('--reports', type=Path, required=True)
    q.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'validate-program':
        program = validate_program(read(a.program))
        result = {'status': 'plan_structure_checked_only', 'experiments': len(program['experiments']),
                  'physical_execution_authorized': False}
    elif a.command == 'plan':
        result = enumerate_design(read(a.program), a.design, a.blocks)
    elif a.command == 'budget':
        result = budget(read(a.program), a.design, a.blocks, a.episode_minutes, a.setup_minutes)
    elif a.command == 'overlap-families':
        result = overlap_families(read(a.windows))
    elif a.command == 'account':
        result = reconstruct(a.episode, read(a.pins))
    else:
        result = compare(read(a.manifest), read(a.reports))
    write_new(a.output, result)
    print(str(a.output), flush=True)


if __name__ == '__main__':
    main()
