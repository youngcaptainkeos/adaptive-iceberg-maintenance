#!/usr/bin/env python3
"""Read-only preflight; never starts Spark, generates workload, or rewrites data."""
import argparse
import json
import sys
from experiment_validation import experiment_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--check-live', action='store_true', help='Read declared engine/table metadata.')
    parser.add_argument('--model-dir', help='Verify accepted model artifacts as well.')
    args = parser.parse_args()
    try:
        _, _, report = experiment_manifest(args.manifest, args.check_live, args.model_dir)
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc)}))
        return 2
    print(json.dumps({'status': 'PASS', **report}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
