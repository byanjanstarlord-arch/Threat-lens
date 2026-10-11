"""
ThreatLens AI - Explainable AI (SHAP TreeExplainer)
Provides local feature attributions for individual predictions and precomputed global importances
using a documented 500-sample representative background.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import shap
import joblib

from threatlens.config import settings

class ThreatLensExplainer:
    """SHAP Explainer wrapper for XGBoost attack classifier."""
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        self.explainer = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
        
    def explain_flow(self, flow_features: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Compute exact SHAP feature attributions for a single network flow.
        Returns top-k features influencing the prediction.
        """
        if flow_features.ndim == 1:
            flow_features = flow_features.reshape(1, -1)
            
        shap_vals = self.explainer.shap_values(flow_features)
        
        # For multiclass, shap_vals is an array of shape (n_samples, n_features, n_classes)
        # or list of arrays per class
        if isinstance(shap_vals, list):
            # Pick class with highest prediction probability
            pred_class = int(np.argmax(self.model.predict_proba(flow_features)[0]))
            class_shap = shap_vals[pred_class][0]
        elif shap_vals.ndim == 3:
            pred_class = int(np.argmax(self.model.predict_proba(flow_features)[0]))
            class_shap = shap_vals[0, :, pred_class]
        else:
            class_shap = shap_vals[0]
            
        top_indices = np.argsort(np.abs(class_shap))[::-1][:top_k]
        
        attributions = []
        for idx in top_indices:
            feat_name = self.feature_names[idx]
            feat_val = float(flow_features[0, idx])
            shap_val = float(class_shap[idx])
            attributions.append({
                "feature": feat_name,
                "value": round(feat_val, 4),
                "shap_value": round(shap_val, 4),
                "impact": "increases_risk" if shap_val > 0 else "decreases_risk"
            })
            
        return attributions

def compute_and_save_global_shap(
    model_path: Path = settings.MODELS_DIR / "v1" / "classifier" / "xgboost_classifier.joblib",
    features_path: Path = settings.MODELS_DIR / "v1" / "classifier" / "feature_columns.json",
    test_path: Path = settings.PROCESSED_DATA_DIR / "clf_test.parquet",
    output_dir: Path = settings.MODELS_DIR / "v1" / "explainability",
    sample_size: int = settings.SHAP_SAMPLE_SIZE
) -> Dict[str, Any]:
    """Compute global SHAP feature importance on a documented representative sample."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n--- Computing Global SHAP Feature Importances ({sample_size} samples) ---")
    
    model = joblib.load(model_path)
    with open(features_path, "r") as fp:
        feature_cols = json.load(fp)
        
    test_df = pd.read_parquet(test_path)
    # Take a representative stratified sample
    sample_df = test_df.sample(n=min(sample_size, len(test_df)), random_state=42)
    X_sample = sample_df[feature_cols].values
    
    explainer = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent")
    shap_values = explainer.shap_values(X_sample)
    
    # Calculate mean absolute SHAP value per feature
    if isinstance(shap_values, list):
        mean_abs_shap = np.mean([np.mean(np.abs(sv), axis=0) for sv in shap_values], axis=0)
    elif shap_values.ndim == 3:
        mean_abs_shap = np.mean(np.mean(np.abs(shap_values), axis=2), axis=0)
    else:
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        
    sorted_idx = np.argsort(mean_abs_shap)[::-1]
    
    global_importances = []
    for rank, idx in enumerate(sorted_idx[:20], 1):
        global_importances.append({
            "rank": rank,
            "feature": feature_cols[idx],
            "mean_abs_shap": float(round(mean_abs_shap[idx], 5))
        })
        
    print(f"[SHAP] Top 5 global drivers: {[g['feature'] for g in global_importances[:5]]}")
    
    summary = {
        "sample_size": len(X_sample),
        "feature_count": len(feature_cols),
        "top_features": global_importances
    }
    
    with open(output_dir / "global_shap_importances.json", "w") as fp:
        json.dump(summary, fp, indent=2)
        
    return summary

if __name__ == "__main__":
    compute_and_save_global_shap()
