"""
ThreatLens AI - Train Anomaly Detector CLI
python -m threatlens.ml.train_anomaly
"""

from threatlens.ml.anomaly import train_and_evaluate_anomaly_detector

if __name__ == "__main__":
    train_and_evaluate_anomaly_detector()
