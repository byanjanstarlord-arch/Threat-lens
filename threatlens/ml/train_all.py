"""
ThreatLens AI - Master Sequential Training Pipeline
Executes:
1. Random Forest baseline -> evaluation
2. XGBoost Multiclass Classifier -> evaluation
3. Unseen attack evaluation
4. Isolation Forest Anomaly Detector -> evaluation
5. Temporal Forecaster (XGBoost) -> evaluation + lead time
6. SHAP feature importance calculation
7. Model Registry registration under version v1
"""

import sys
import gc
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from threatlens.config import settings
from threatlens.ml.classifier import train_and_evaluate_classifier
from threatlens.ml.anomaly import train_and_evaluate_anomaly_detector
from threatlens.ml.forecaster import train_and_evaluate_forecaster
from threatlens.ml.explainability import compute_and_save_global_shap
from threatlens.ml.registry import registry

def run_full_training_pipeline(version: str = "v1"):
    print("=" * 70)
    print(f"THREATLENS AI - SEQUENTIAL MODEL TRAINING (VERSION: {version})")
    print(f"Execution Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    start_all = time.time()
    v_dir = settings.MODELS_DIR / version
    v_dir.mkdir(parents=True, exist_ok=True)
    
    # 1 & 2. Classifier Training (Random Forest & XGBoost)
    print("\n[Stage 1/5] Training Classifiers (RF Baseline & XGBoost)...")
    clf_metrics = train_and_evaluate_classifier(output_dir=v_dir / "classifier")
    gc.collect()
    
    # 3. Anomaly Detector (Isolation Forest on Benign Baseline)
    print("\n[Stage 2/5] Training Anomaly Detector (Isolation Forest)...")
    anom_metrics = train_and_evaluate_anomaly_detector(output_dir=v_dir / "anomaly")
    gc.collect()
    
    # 4. Temporal Forecaster (XGBoost on 1-minute windows, 5-minute horizon)
    print("\n[Stage 3/5] Training Temporal Attack Forecaster...")
    fc_metrics = train_and_evaluate_forecaster(output_dir=v_dir / "forecasting")
    gc.collect()
    
    # 5. Explainable AI (SHAP Global Importances)
    print("\n[Stage 4/5] Computing Global SHAP Feature Attributions...")
    shap_summary = compute_and_save_global_shap(
        model_path=v_dir / "classifier" / "xgboost_classifier.joblib",
        features_path=v_dir / "classifier" / "feature_columns.json",
        output_dir=v_dir / "explainability"
    )
    gc.collect()
    
    # 6. Model Registry Registration
    print("\n[Stage 5/5] Registering Trained Version in Model Registry...")
    combined_metrics = {
        "classifier": clf_metrics,
        "anomaly_detector": anom_metrics,
        "forecaster": fc_metrics,
        "explainability": shap_summary
    }
    
    # Load data quality report for dataset provenance
    dqr_path = settings.REPORTS_DIR / "data_quality_report.json"
    dataset_info = {}
    if dqr_path.exists():
        with open(dqr_path, "r") as fp:
            dataset_info = json.load(fp)
            
    registry.register_version(
        version=version,
        metrics=combined_metrics,
        dataset_info=dataset_info,
        status="active"
    )
    
    total_time = round(time.time() - start_all, 2)
    print("\n" + "=" * 70)
    print(f"TRAINING COMPLETE IN {total_time} SECONDS")
    print("=" * 70)
    print(f"Random Forest Macro F1: {clf_metrics['random_forest']['macro_f1']:.4f}")
    print(f"XGBoost Classifier Macro F1: {clf_metrics['xgboost']['macro_f1']:.4f}")
    print(f"Isolation Forest Test ROC-AUC: {anom_metrics['test_roc_auc']:.4f}")
    print(f"Temporal Forecaster Test F1: {fc_metrics['f1_score']:.4f}, PR-AUC: {fc_metrics['pr_auc']:.4f}")
    print(f"Mean Early Warning Lead Time: {fc_metrics['lead_time_metrics']['mean_lead_time_sec']:.1f} seconds")
    print(f"Model Artifacts Directory: {v_dir}")
    print(f"Active Model Registry: {settings.MODELS_DIR / 'registry.json'}")

if __name__ == "__main__":
    run_full_training_pipeline()
