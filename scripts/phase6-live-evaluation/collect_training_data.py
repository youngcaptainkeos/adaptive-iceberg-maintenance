#!/usr/bin/env python3
"""Retired collector entry point. Physical correctness tools do not approve collection."""
import argparse
from experiment_validation import experiment_manifest, ValidationError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    experiment_manifest(args.manifest, check_live=True)
    raise ValidationError('Collection remains blocked: require accepted original-timing arrival replay, matched experiment protocol, pre-query state evidence and reviewed event export. Legacy closed-loop delays and random self-inserts are retired.')


if __name__ == '__main__':
    main()
