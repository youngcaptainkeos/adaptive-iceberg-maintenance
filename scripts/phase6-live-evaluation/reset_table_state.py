#!/usr/bin/env python3
"""Fail closed: implicit earliest-snapshot reset is no longer permitted."""
import argparse
from experiment_validation import experiment_manifest, ValidationError


def reset_table_layout(*, manifest_path):
    experiment_manifest(manifest_path, check_live=True)
    raise ValidationError('Reset is blocked pending explicit target-snapshot provenance and verified reset/postconditions in the repaired harness.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    reset_table_layout(manifest_path=args.manifest)


if __name__ == '__main__':
    main()
