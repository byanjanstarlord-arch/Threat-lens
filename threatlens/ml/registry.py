"""
ThreatLens AI - Model Registry and Version Manager
Maintains versioned model metadata, provenance, and unified inference interfaces.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import joblib

from threatlens.config import settings
from threatlens.data.clean import FlowPreprocessor
from threatlens.ml.anomaly import ThreatLensAnomalyDetector
from threatlens.ml.explainability import ThreatLensExplainer
from threatlens.ml.risk_engine import RiskEngine, risk_engine

REGISTRY_FILE = settings.MODELS_DIR / "registry.json"

class ModelRegistry:
    """Manages model artifacts, metadata, and production inference sessions."""
    def __init__(self, models_dir: Path = settings.MODELS_DIR):
        self.models_dir = models_dir
        self.active_version = "v1"
        self._loaded_models: Dict[str, Any] = {}
        
    def get_registry_manifest(self) -> Dict[str, Any]:
        """Read or initialize the model registry manifest."""
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, "r") as fp:
                return json.load(fp)
        return {"active_version": "v1", "versions": {}}

    def register_version(
        self,
        version: str,
        metrics: Dict[str, Any],
        dataset_info: Dict[str, Any],
        status: str = "active"
    ):
        """Register a new trained model version with provenance."""
        manifest = self.get_registry_manifest()
        manifest["versions"][version] = {
            "version": version,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "metrics": metrics,
            "dataset": dataset_info,
            "artifacts_dir": str(self.models_dir / version)
        }
        if status == "active":
            manifest["active_version"] = version
            self.active_version = version
            
        with open(REGISTRY_FILE, "w") as fp:
            json.dump(manifest, fp, indent=2)

    def load_active_pipeline(self):
        """Load production model suite into memory once for high-throughput inference."""
        if self._loaded_models:
            return self._loaded_models
            
        manifest = self.get_registry_manifest()
        active_ver = manifest.get("active_version", "v1")
        version_dir = self.models_dir / active_ver
        
        preprocessor_path = settings.MODELS_DIR / "preprocessor.joblib"
        if not preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor not found at {preprocessor_path}")
            
        clf_dir = version_dir / "classifier"
        anom_dir = version_dir / "anomaly"
        fc_dir = version_dir / "forecasting"
        
        preprocessor = FlowPreprocessor.load(preprocessor_path)
        clf = joblib.load(clf_dir / "xgboost_classifier.joblib")
        label_encoder = joblib.load(clf_dir / "label_encoder.joblib")
        anom = joblib.load(anom_dir / "isolation_forest.joblib")
        forecaster = joblib.load(fc_dir / "xgboost_forecaster.joblib")
        
        with open(clf_dir / "feature_columns.json", "r") as fp:
            clf_features = json.load(fp)
        with open(fc_dir / "forecaster_features.json", "r") as fp:
            fc_features = json.load(fp)
            
        explainer = ThreatLensExplainer(clf, clf_features)
        
        self._loaded_models = {
            "version": active_ver,
            "preprocessor": preprocessor,
            "classifier": clf,
            "label_encoder": label_encoder,
            "clf_features": clf_features,
            "anomaly_detector": anom,
            "forecaster": forecaster,
            "fc_features": fc_features,
            "explainer": explainer,
            "risk_engine": risk_engine
        }
        return self._loaded_models

# Global singleton
registry = ModelRegistry()
