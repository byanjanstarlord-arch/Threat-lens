"""
ThreatLens AI - Attack Classification Engine (Track A)
Implements:
1. Random Forest Baseline Classifier
2. XGBoost Multiclass Attack Classifier
3. Unseen / Unknown Attack Evaluation
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
import xgboost as xgb
import joblib

from threatlens.config import settings

def train_and_evaluate_classifier(
    train_path: Path = settings.PROCESSED_DATA_DIR / "clf_train.parquet",
    val_path: Path = settings.PROCESSED_DATA_DIR / "clf_val.parquet",
    test_path: Path = settings.PROCESSED_DATA_DIR / "clf_test.parquet",
    output_dir: Path = settings.MODELS_DIR / "v1" / "classifier"
) -> Dict[str, Any]:
    """
    Train Random Forest baseline and XGBoost classifier sequentially on Track A partitions.
    Computes exact, un-fabricated metrics on the test partition.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("[Classifier] Loading Track A partitions...")
    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)
    
    feature_cols = [c for c in train_df.columns if c != "Label"]
    
    # Encode targets deterministically
    label_encoder = LabelEncoder()
    label_encoder.fit(settings.TAXONOMY_CLASSES)
    
    X_train, y_train = train_df[feature_cols].values, label_encoder.transform(train_df["Label"])
    X_val, y_val = val_df[feature_cols].values, label_encoder.transform(val_df["Label"])
    X_test, y_test = test_df[feature_cols].values, label_encoder.transform(test_df["Label"])
    
    classes_list = list(label_encoder.classes_)
    print(f"[Classifier] Classes ({len(classes_list)}): {classes_list}")
    print(f"[Classifier] Train samples: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")

    results = {}

    # -------------------------------------------------------------------------
    # 1. Random Forest Baseline
    # -------------------------------------------------------------------------
    print("\n--- 1. Training Random Forest Baseline ---")
    rf_start = time.time()
    rf = RandomForestClassifier(
        n_estimators=80,
        max_depth=16,
        class_weight="balanced",
        n_jobs=settings.N_JOBS,
        random_state=42
    )
    rf.fit(X_train, y_train)
    rf_train_time = round(time.time() - rf_start, 2)
    print(f"[RF] Training completed in {rf_train_time}s")
    
    y_pred_rf = rf.predict(X_test)
    rf_metrics = {
        "model_type": "RandomForest",
        "train_time_sec": rf_train_time,
        "macro_f1": float(f1_score(y_test, y_pred_rf, average="macro")),
        "weighted_f1": float(f1_score(y_test, y_pred_rf, average="weighted")),
        "macro_precision": float(precision_score(y_test, y_pred_rf, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_test, y_pred_rf, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_test, y_pred_rf).tolist(),
        "classification_report": classification_report(y_test, y_pred_rf, target_names=classes_list, output_dict=True, zero_division=0)
    }
    print(f"[RF] Test Macro F1: {rf_metrics['macro_f1']:.4f}, Weighted F1: {rf_metrics['weighted_f1']:.4f}")
    
    # Save RF Model
    joblib.dump(rf, output_dir / "random_forest_baseline.joblib")
    results["random_forest"] = rf_metrics

    # -------------------------------------------------------------------------
    # 2. XGBoost Multiclass Classifier
    # -------------------------------------------------------------------------
    print("\n--- 2. Training XGBoost Multiclass Classifier ---")
    xgb_start = time.time()
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=7,
        learning_rate=0.1,
        tree_method="hist",
        n_jobs=settings.N_JOBS,
        random_state=42,
        eval_metric="mlogloss"
    )
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    xgb_train_time = round(time.time() - xgb_start, 2)
    print(f"[XGBoost] Training completed in {xgb_train_time}s")
    
    y_pred_xgb = xgb_model.predict(X_test)
    y_prob_xgb = xgb_model.predict_proba(X_test)
    
    # Calculate False Positive Rate on BENIGN
    benign_idx = classes_list.index("BENIGN")
    benign_mask = (y_test == benign_idx)
    fp_count = int(np.sum((y_pred_xgb != benign_idx) & benign_mask))
    tn_count = int(np.sum((y_pred_xgb == benign_idx) & benign_mask))
    benign_fpr = float(fp_count / max(1, fp_count + tn_count))

    xgb_metrics = {
        "model_type": "XGBoost",
        "train_time_sec": xgb_train_time,
        "macro_f1": float(f1_score(y_test, y_pred_xgb, average="macro")),
        "weighted_f1": float(f1_score(y_test, y_pred_xgb, average="weighted")),
        "macro_precision": float(precision_score(y_test, y_pred_xgb, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_test, y_pred_xgb, average="macro", zero_division=0)),
        "benign_false_positive_rate": benign_fpr,
        "confusion_matrix": confusion_matrix(y_test, y_pred_xgb).tolist(),
        "classification_report": classification_report(y_test, y_pred_xgb, target_names=classes_list, output_dict=True, zero_division=0)
    }
    print(f"[XGBoost] Test Macro F1: {xgb_metrics['macro_f1']:.4f}, Weighted F1: {xgb_metrics['weighted_f1']:.4f}, Benign FPR: {benign_fpr:.4f}")

    # Save active model, label encoder, and feature columns
    joblib.dump(xgb_model, output_dir / "xgboost_classifier.joblib")
    joblib.dump(label_encoder, output_dir / "label_encoder.joblib")
    
    with open(output_dir / "feature_columns.json", "w") as fp:
        json.dump(feature_cols, fp, indent=2)
        
    results["xgboost"] = xgb_metrics

    # -------------------------------------------------------------------------
    # 3. Unseen / Unknown Attack Evaluation Experiment
    # -------------------------------------------------------------------------
    print("\n--- 3. Unseen Attack Evaluation Experiment ---")
    # Evaluate how the trained classifier reacts to held-out attack samples
    unseen_target = "BOTNET"
    unseen_mask = (test_df["Label"] == unseen_target)
    if unseen_mask.sum() > 0:
        X_unseen = test_df.loc[unseen_mask, feature_cols].values
        unseen_preds = xgb_model.predict(X_unseen)
        unseen_pred_labels = [classes_list[idx] for idx in unseen_preds]
        pred_dist = pd.Series(unseen_pred_labels).value_counts().to_dict()
        flagged_non_benign_pct = float(np.mean([lbl != "BENIGN" for lbl in unseen_pred_labels]) * 100)
        
        unseen_eval = {
            "unseen_attack_category": unseen_target,
            "sample_count": int(unseen_mask.sum()),
            "predicted_distribution": pred_dist,
            "flagged_as_threat_percentage": flagged_non_benign_pct
        }
        print(f"[Unseen Evaluation] {unseen_target} flows ({len(X_unseen)}): {flagged_non_benign_pct:.2f}% flagged as non-benign threat")
        results["unseen_attack_evaluation"] = unseen_eval

    # Persist all metrics
    metrics_path = output_dir / "classifier_metrics.json"
    with open(metrics_path, "w") as fp:
        json.dump(results, fp, indent=2)
        
    print(f"[Classifier] Evaluation metrics saved to {metrics_path}")
    return results

if __name__ == "__main__":
    train_and_evaluate_classifier()
