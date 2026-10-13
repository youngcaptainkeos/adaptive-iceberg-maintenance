#!/usr/bin/env python3
"""Retired evaluator; validated cost artifacts alone do not authorize a scheduler."""
import argparse
import os
import joblib
from experiment_validation import experiment_manifest, validate_model_bundle, require, ValidationError


class CostBenefitPolicy:
    """Historical accepted-bundle loader; decision logic awaits measured planning."""
    def __init__(self, *, model_dir):
        self.metadata = validate_model_bundle(model_dir)
        self.model_a = joblib.load(os.path.join(model_dir, self.metadata['model_a']['artifact']['path']))
        self.model_b = joblib.load(os.path.join(model_dir, self.metadata['model_b']['artifact']['path']))
        self.features = self.metadata['features']
        for model in (self.model_a, self.model_b):
            require(list(model.feature_names_in_) == self.features, 'Model feature schema mismatch.')

    def decide(self, telemetry):
        raise ValidationError('Decision unavailable: no verified common-horizon planner, forecast or measured state-transition model. Fixed file increments and comparisons of two upper bounds are retired.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--model-dir')
    args = parser.parse_args()
    experiment_manifest(args.manifest, check_live=True, model_dir=args.model_dir)
    raise ValidationError('Publication evaluation remains blocked pending accepted workload mapping, matched cost data, forecast-aware planning and faithful baselines.')


if __name__ == '__main__':
    main()
