"""
ThreatLens AI - Anomaly Detection Engine
Implements Isolation Forest trained strictly on Benign baseline traffic.
Distinct from classification: detects behavioral deviation from normal baseline.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
import joblib

from threatlens.config import settings

class ThreatLensAnomalyDetector:
    """Production wrapper for calibrated Isolation Forest anomaly detector."""
    def __init__(self, contamination: float = 0.03):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=100,
            max_samples="auto",
            contamination=contamination,
            n_jobs=settings.N_JOBS,
            random_state=42
        )
        self.threshold: float = 0.5
        self.fitted: bool = False
        self.feature_columns: list = []

    def fit(self, X_benign: np.ndarray, feature_cols: list):
        self.feature_columns = feature_cols
        self.model.fit(X_benign)
        # Compute raw decision function on training benign
        raw_scores = -self.model.score_samples(X_benign)
        # Calibrate threshold at (1 - contamination) quantile
        self.threshold = float(np.percentile(raw_scores, (1.0 - self.contamination) * 100))
        self.fitted = True
        return self

    def score(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute anomaly score normalized to [0, 1] and boolean is_anomalous flag.
        Score = 1.0 means extreme deviation from benign baseline.
        """
        if not self.fitted:
            raise ValueError("Model not fitted.")
        raw_scores = -self.model.score_samples(X)
        # Sigmoid normalization around threshold
        normalized_scores = 1.0 / (1.0 + np.exp(-(raw_scores - self.threshold) * 8.0))
        is_anomalous = (raw_scores >= self.threshold).astype(int)
        return normalized_scores, is_anomalous

def train_and_evaluate_anomaly_detector(
    train_path: Path = settings.PROCESSED_DATA_DIR / "clf_train.parquet",
    test_path: Path = settings.PROCESSED_DATA_DIR / "clf_test.parquet",
    output_dir: Path = settings.MODELS_DIR / "v1" / "anomaly"
) -> Dict[str, Any]:
    """Train Isolation Forest on benign flows and evaluate separation on test partition."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\n--- Training Anomaly Detector (Isolation Forest) ---")
    
    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)
    
    feature_cols = [c for c in train_df.columns if c != "Label"]
    
    # Train STRICTLY on BENIGN flows
    benign_train = train_df[train_df["Label"] == "BENIGN"]
    X_benign_train = benign_train[feature_cols].values
    print(f"[Anomaly] Training on {len(X_benign_train):,} normal benign flows...")
    
    start_t = time.time()
    detector = ThreatLensAnomalyDetector(contamination=0.03)
    detector.fit(X_benign_train, feature_cols)
    train_time = round(time.time() - start_t, 2)
    print(f"[Anomaly] Isolation Forest fitted in {train_time}s. Calibrated threshold: {detector.threshold:.4f}")
    
    # Evaluate on Test Partition
    X_test = test_df[feature_cols].values
    y_test_is_threat = (test_df["Label"] != "BENIGN").astype(int).values
    
    scores, is_anom = detector.score(X_test)
    
    # Calculate ROC-AUC against binary attack status
    roc_auc = float(roc_auc_score(y_test_is_threat, scores))
    benign_anom_rate = float(np.mean(is_anom[y_test_is_threat == 0]))
    attack_anom_rate = float(np.mean(is_anom[y_test_is_threat == 1]))
    
    metrics = {
        "model_type": "IsolationForest",
        "train_time_sec": train_time,
        "calibrated_threshold": detector.threshold,
        "test_roc_auc": roc_auc,
        "benign_false_alarm_rate": benign_anom_rate,
        "attack_detection_rate": attack_anom_rate,
        "total_test_evaluated": len(test_df)
    }
    
    print(f"[Anomaly] Test ROC-AUC: {roc_auc:.4f}, Benign False Alarm: {benign_anom_rate:.4f}, Attack Flag Rate: {attack_anom_rate:.4f}")
    
    # Save artifacts
    joblib.dump(detector, output_dir / "isolation_forest.joblib")
    with open(output_dir / "anomaly_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=2)
        
    return metrics

if __name__ == "__main__":
    train_and_evaluate_anomaly_detector()
