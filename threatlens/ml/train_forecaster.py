"""
ThreatLens AI - Train Temporal Forecaster CLI
python -m threatlens.ml.train_forecaster
"""

from threatlens.ml.forecaster import train_and_evaluate_forecaster

if __name__ == "__main__":
    train_and_evaluate_forecaster()
