"""
ThreatLens AI - Temporal Attack Forecasting Engine (Track B)
Predicts attack likelihood in future 5-minute horizon using strictly backward-looking 1-minute window features.
Computes empirical early warning lead time.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix
)
import xgboost as xgb
import joblib

from threatlens.config import settings

FORECAST_FEATURE_COLS = [
    "flow_count",
    "total_bytes",
    "total_packets",
    "byte_rate",
    "packet_rate",
    "syn_flag_count",
    "ack_flag_count",
    "fin_flag_count",
    "rst_flag_count",
    "mean_flow_duration",
    "rolling_mean_flow_count_3",
    "rolling_mean_byte_rate_3",
    "rolling_max_packet_rate_3",
    "flow_growth_rate"
]

def engineer_window_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived behavioral interaction features from window telemetry."""
    out = df.copy()
    # Compute safe ratios
    out["syn_to_ack_ratio"] = (out["syn_flag_count"] / (out["ack_flag_count"] + 1.0)).clip(upper=1000.0)
    out["bytes_per_packet"] = (out["total_bytes"] / (out["total_packets"] + 1.0)).clip(upper=65535.0)
    return out

def train_and_evaluate_forecaster(
    train_path: Path = settings.PROCESSED_DATA_DIR / "forecast_train.parquet",
    val_path: Path = settings.PROCESSED_DATA_DIR / "forecast_val.parquet",
    test_path: Path = settings.PROCESSED_DATA_DIR / "forecast_test.parquet",
    output_dir: Path = settings.MODELS_DIR / "v1" / "forecasting"
) -> Dict[str, Any]:
    """
    Train temporal forecasting model on chronological session windows.
    Evaluates warning lead time and prediction quality on out-of-time test session.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\n--- Training Attack Forecaster (XGBoost Temporal) ---")
    
    train_df = engineer_window_features(pd.read_parquet(train_path))
    val_df = engineer_window_features(pd.read_parquet(val_path))
    test_df = engineer_window_features(pd.read_parquet(test_path))
    
    feature_cols = FORECAST_FEATURE_COLS + ["syn_to_ack_ratio", "bytes_per_packet"]
    
    X_train, y_train = train_df[feature_cols].values, train_df["future_attack"].values
    X_val, y_val = val_df[feature_cols].values, val_df["future_attack"].values
    X_test, y_test = test_df[feature_cols].values, test_df["future_attack"].values
    
    print(f"[Forecaster] Window counts: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    print(f"[Forecaster] Test base attack rate: {np.mean(y_test)*100:.1f}%")
    
    start_t = time.time()
    # Calculate scale_pos_weight
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    spw = float(neg_count / max(1, pos_count))
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        scale_pos_weight=spw,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=settings.N_JOBS,
        random_state=42,
        eval_metric="logloss"
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    train_time = round(time.time() - start_t, 2)
    print(f"[Forecaster] Trained in {train_time}s")
    
    # Evaluate on Test Partition (Friday Out-of-Time Session)
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    
    # Compute standard classification & ranking metrics
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0
    pr_auc = float(average_precision_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0
    
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    fpr = float(fp / max(1, fp + tn))
    fnr = float(fn / max(1, fn + tp))
    
    # -------------------------------------------------------------------------
    # Empirical Forecast Warning Lead Time Calculation
    # -------------------------------------------------------------------------
    # For every True Positive alert (model predicted future attack and attack actually occurred)
    tp_mask = (y_pred == 1) & (y_test == 1)
    observed_lead_times = test_df.loc[tp_mask, "lead_time_sec"].dropna().values
    
    if len(observed_lead_times) > 0:
        lead_time_metrics = {
            "mean_lead_time_sec": float(np.mean(observed_lead_times)),
            "median_lead_time_sec": float(np.median(observed_lead_times)),
            "min_lead_time_sec": float(np.min(observed_lead_times)),
            "max_lead_time_sec": float(np.max(observed_lead_times)),
            "evaluated_warnings_count": int(len(observed_lead_times))
        }
    else:
        lead_time_metrics = {
            "mean_lead_time_sec": 0.0,
            "median_lead_time_sec": 0.0,
            "min_lead_time_sec": 0.0,
            "max_lead_time_sec": 0.0,
            "evaluated_warnings_count": 0
        }
        
    print(f"[Forecaster] Test F1: {f1:.4f}, Precision: {prec:.4f}, Recall: {rec:.4f}, PR-AUC: {pr_auc:.4f}")
    print(f"[Forecaster] Lead Time: Mean={lead_time_metrics['mean_lead_time_sec']:.1f}s, Median={lead_time_metrics['median_lead_time_sec']:.1f}s")
    
    metrics = {
        "model_type": "XGBoostForecaster",
        "train_time_sec": train_time,
        "window_size_sec": settings.WINDOW_SIZE_SECONDS,
        "forecast_horizon_sec": settings.FORECAST_HORIZON_SECONDS,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "confusion_matrix": cm.tolist(),
        "lead_time_metrics": lead_time_metrics
    }
    
    # Save artifacts
    joblib.dump(model, output_dir / "xgboost_forecaster.joblib")
    with open(output_dir / "forecaster_features.json", "w") as fp:
        json.dump(feature_cols, fp, indent=2)
    with open(output_dir / "forecaster_metrics.json", "w") as fp:
        json.dump(metrics, fp, indent=2)
        
    return metrics

if __name__ == "__main__":
    train_and_evaluate_forecaster()
