"""
ThreatLens AI - Model Evaluation & Metrics Summary CLI
python -m threatlens.ml.evaluate
"""

import json
from threatlens.config import settings
from threatlens.ml.registry import registry

def main():
    print("=" * 65)
    print("THREATLENS AI - MODEL PERFORMANCE EVALUATION REPORT")
    print("=" * 65)
    manifest = registry.get_registry_manifest()
    act_ver = manifest.get("active_version", "v1")
    v_data = manifest.get("versions", {}).get(act_ver)
    
    if not v_data:
        print("No trained model version registered.")
        return
        
    metrics = v_data.get("metrics", {})
    clf = metrics.get("classifier", {}).get("xgboost", {})
    rf = metrics.get("classifier", {}).get("random_forest", {})
    anom = metrics.get("anomaly_detector", {})
    fc = metrics.get("forecaster", {})
    unseen = metrics.get("classifier", {}).get("unseen_attack_evaluation", {})
    
    print(f"Active Version: {act_ver}")
    print(f"Registered At: {v_data.get('registered_at')}")
    print("\n--- Track A: Attack Classification Track (Test Partition) ---")
    print(f"  Random Forest Baseline Macro F1: {rf.get('macro_f1', 0):.4f}")
    print(f"  XGBoost Classifier Macro F1:     {clf.get('macro_f1', 0):.4f}")
    print(f"  XGBoost Weighted F1:             {clf.get('weighted_f1', 0):.4f}")
    print(f"  Benign False Positive Rate:      {clf.get('benign_false_positive_rate', 0)*100:.2f}%")
    
    if unseen:
        print("\n--- Unseen Attack Generalization Experiment ---")
        print(f"  Held-Out Class:                  {unseen.get('unseen_attack_category')}")
        print(f"  Flagged as Non-Benign Threat:    {unseen.get('flagged_as_threat_percentage', 0):.2f}%")
        
    print("\n--- Anomaly Detection (Isolation Forest on Benign Baseline) ---")
    print(f"  Test ROC-AUC:                    {anom.get('test_roc_auc', 0):.4f}")
    print(f"  Benign False Alarm Rate:         {anom.get('benign_false_alarm_rate', 0)*100:.2f}%")
    
    print("\n--- Track B: Temporal Attack Forecasting (Out-of-Time Test) ---")
    print(f"  Forecast Horizon:                5 Minutes (300 seconds)")
    print(f"  Precision:                       {fc.get('precision', 0):.4f}")
    print(f"  Recall:                          {fc.get('recall', 0):.4f}")
    print(f"  F1 Score:                        {fc.get('f1_score', 0):.4f}")
    print(f"  PR-AUC:                          {fc.get('pr_auc', 0):.4f}")
    lt = fc.get("lead_time_metrics", {})
    print(f"  Mean Warning Lead Time:          {lt.get('mean_lead_time_sec', 0):.1f} seconds")
    print("=" * 65)

if __name__ == "__main__":
    main()
