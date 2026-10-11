"""
ThreatLens AI - Prediction Service
Coordinates Flow Preprocessing, XGBoost Classifier, Isolation Forest,
SHAP Explanations, Risk Engine, and Database Persistence.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from threatlens.ml.registry import registry
from threatlens.backend.models_db import Prediction, AttackEvent, Alert
from threatlens.backend.schemas import PredictResponse, SHAPFeature

class PredictionService:
    def __init__(self):
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = registry.load_active_pipeline()
        return self._pipeline

    def predict_single_flow(
        self,
        features_dict: Dict[str, float],
        db: Session,
        forecast_prob: float = 0.0,
        flow_index: int = None
    ) -> PredictResponse:
        pipe = self.pipeline
        preprocessor = pipe["preprocessor"]
        clf = pipe["classifier"]
        label_encoder = pipe["label_encoder"]
        anom = pipe["anomaly_detector"]
        explainer = pipe["explainer"]
        risk_eng = pipe["risk_engine"]
        version = pipe["version"]
        
        # Format input dataframe and transform
        raw_df = pd.DataFrame([features_dict])
        clean_df = preprocessor.transform(raw_df)
        X_vec = clean_df.values.astype(np.float32)
        
        # 1. Classification
        class_probs = clf.predict_proba(X_vec)[0]
        pred_idx = int(np.argmax(class_probs))
        pred_class = str(label_encoder.classes_[pred_idx])
        confidence = float(class_probs[pred_idx])
        
        # Estimated attack probability (sum of all attack classes)
        benign_idx = list(label_encoder.classes_).index("BENIGN")
        clf_attack_prob = float(1.0 - class_probs[benign_idx])
        
        # 2. Anomaly Detection
        anom_scores, is_anom_flags = anom.score(X_vec)
        anomaly_score = float(anom_scores[0])
        is_anomalous = bool(is_anom_flags[0])
        
        # 3. Composite Risk Evaluation
        risk_res = risk_eng.evaluate_risk(
            classifier_prob=clf_attack_prob,
            anomaly_score=anomaly_score,
            forecast_prob=forecast_prob,
            predicted_category=pred_class
        )
        
        # 4. SHAP Feature Attribution
        raw_attributions = explainer.explain_flow(X_vec[0], top_k=5)
        shap_items = [SHAPFeature(**attr) for attr in raw_attributions]
        
        # 5. Database Persistence
        db_pred = Prediction(
            flow_index=flow_index,
            model_version=version,
            predicted_class=pred_class,
            confidence=confidence,
            anomaly_score=anomaly_score,
            is_anomalous=is_anomalous,
            composite_risk=risk_res["composite_risk_score"],
            risk_level=risk_res["risk_level"],
            shap_features=raw_attributions
        )
        db.add(db_pred)
        db.flush()
        
        # Store attack event if confirmed threat
        if pred_class != "BENIGN":
            dest_port = int(features_dict.get("Destination Port", 0))
            db_attack = AttackEvent(
                attack_type=pred_class,
                confidence=confidence,
                risk_level=risk_res["risk_level"],
                model_version=version,
                destination_port=dest_port,
                details={"shap_drivers": [a.feature for a in shap_items[:3]]}
            )
            db.add(db_attack)
            
        # Store alert if risk is elevated
        if risk_res["should_alert"]:
            db_alert = Alert(
                alert_type=f"{risk_res['risk_level']} RISK DETECTED",
                severity=risk_res["risk_level"],
                title=f"Detected {pred_class} Threat Event",
                message=f"Flow flagged with {confidence*100:.1f}% confidence. Composite risk: {risk_res['composite_risk_score']*100:.1f}%.",
                source_event_type="PREDICTION",
                source_event_id=db_pred.id,
                status="UNRESOLVED"
            )
            db.add(db_alert)
            
        db.commit()
        
        return PredictResponse(
            model_version=version,
            predicted_class=pred_class,
            confidence=confidence,
            anomaly_score=anomaly_score,
            is_anomalous=is_anomalous,
            composite_risk_score=risk_res["composite_risk_score"],
            risk_level=risk_res["risk_level"],
            should_alert=risk_res["should_alert"],
            risk_assessment=risk_res,
            shap_top_features=shap_items
        )

prediction_service = PredictionService()
