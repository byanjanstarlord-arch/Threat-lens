"""
ThreatLens AI - Forecasting Service
Executes temporal attack forecasting and manages early warning alert generation.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from threatlens.ml.registry import registry
from threatlens.ml.forecaster import engineer_window_features
from threatlens.backend.models_db import ForecastPrediction, Alert
from threatlens.backend.schemas import ForecastResponse

class ForecastingService:
    def __init__(self):
        self._pipeline = None

    @property
    def pipeline(self):
        if self._pipeline is None:
            self._pipeline = registry.load_active_pipeline()
        return self._pipeline

    def predict_window_forecast(
        self,
        window_dict: Dict[str, Any],
        db: Session,
        window_id: int = None,
        actual_attack_occurred: bool = None,
        observed_outcome: str = None,
        lead_time_seconds: float = None
    ) -> ForecastResponse:
        pipe = self.pipeline
        forecaster = pipe["forecaster"]
        fc_features = pipe["fc_features"]
        version = pipe["version"]
        
        # Prepare single-row dataframe and engineer ratios
        df_win = pd.DataFrame([window_dict])
        df_eng = engineer_window_features(df_win)
        
        # Ensure all features exist
        for col in fc_features:
            if col not in df_eng.columns:
                df_eng[col] = 0.0
                
        X_vec = df_eng[fc_features].values.astype(np.float32)
        
        # Forecast attack likelihood
        attack_prob = float(forecaster.predict_proba(X_vec)[0, 1])
        attack_prob = round(attack_prob, 4)
        
        # Categorize risk level
        if attack_prob >= 0.80:
            level = "CRITICAL"
        elif attack_prob >= 0.60:
            level = "HIGH"
        elif attack_prob >= 0.30:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        pred_category = "ATTACK_LIKELY" if attack_prob >= 0.50 else "BENIGN"

        # Extract ground truth from window_dict if not explicitly passed
        if actual_attack_occurred is None and "future_attack" in window_dict:
            actual_attack_occurred = bool(window_dict["future_attack"] == 1)
        if observed_outcome is None and "future_attack_category" in window_dict:
            observed_outcome = str(window_dict["future_attack_category"])
        if lead_time_seconds is None and "lead_time_sec" in window_dict:
            val = window_dict["lead_time_sec"]
            lead_time_seconds = float(val) if not pd.isna(val) else None
        
        # Save to database
        db_fc = ForecastPrediction(
            window_id=window_id,
            model_version=version,
            horizon_seconds=300,
            forecast_attack_prob=attack_prob,
            predicted_category=pred_category,
            risk_level=level,
            actual_attack_occurred=actual_attack_occurred,
            observed_outcome=observed_outcome,
            lead_time_seconds=lead_time_seconds
        )
        db.add(db_fc)
        db.flush()
        
        # Trigger early warning alert if high probability
        if level in ["HIGH", "CRITICAL"]:
            db_alert = Alert(
                alert_type="HIGH RISK FORECAST WARNING",
                severity=level,
                title=f"Early Warning: {level} Attack Risk in Next 5 Minutes",
                message=f"Forecasting model estimates {attack_prob*100:.1f}% probability of malicious activity onset within the 5-minute horizon.",
                source_event_type="FORECAST",
                source_event_id=db_fc.id,
                status="UNRESOLVED"
            )
            db.add(db_alert)
            
        db.commit()
        
        wording = f"Model-estimated attack probability: {attack_prob*100:.1f}% over the 5-minute horizon."
        
        return ForecastResponse(
            model_version=version,
            forecast_horizon_seconds=300,
            forecast_attack_probability=attack_prob,
            risk_level=level,
            confidence_wording=wording,
            predicted_category=pred_category
        )

forecasting_service = ForecastingService()
