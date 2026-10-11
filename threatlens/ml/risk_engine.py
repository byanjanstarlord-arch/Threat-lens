"""
ThreatLens AI - Multi-Factor Risk Assessment Engine
Combines:
1. Classifier attack probability
2. Isolation Forest anomaly score
3. Temporal forecasting attack probability
All weights and risk category thresholds are fully configurable via settings.
"""

from typing import Dict, Any, Optional
from threatlens.config import settings

class RiskEngine:
    """Configurable multi-factor cybersecurity risk evaluation engine."""
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None
    ):
        self.weights = weights or settings.RISK_WEIGHTS.copy()
        self.thresholds = thresholds or settings.RISK_THRESHOLDS.copy()
        
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def evaluate_risk(
        self,
        classifier_prob: float,
        anomaly_score: float,
        forecast_prob: float,
        predicted_category: str = "BENIGN"
    ) -> Dict[str, Any]:
        """
        Evaluate composite risk score and risk level.
        Does not present estimates as absolute certainties.
        """
        # Clamp inputs to [0, 1]
        p_clf = max(0.0, min(1.0, float(classifier_prob)))
        s_anom = max(0.0, min(1.0, float(anomaly_score)))
        p_fc = max(0.0, min(1.0, float(forecast_prob)))
        
        composite_score = (
            self.weights.get("classifier", 0.45) * p_clf +
            self.weights.get("anomaly", 0.25) * s_anom +
            self.weights.get("forecast", 0.30) * p_fc
        )
        composite_score = round(composite_score, 4)
        
        # Categorize risk level based on configured thresholds
        if composite_score >= self.thresholds.get("CRITICAL", 0.85):
            level = "CRITICAL"
        elif composite_score >= self.thresholds.get("HIGH", 0.60):
            level = "HIGH"
        elif composite_score >= self.thresholds.get("MEDIUM", 0.30):
            level = "MEDIUM"
        else:
            level = "LOW"
            
        # Determine alert trigger
        should_alert = (level in ["HIGH", "CRITICAL"]) or (p_clf >= 0.85 and predicted_category != "BENIGN")
        
        # Transparent signal descriptions
        assessment = {
            "composite_risk_score": composite_score,
            "risk_level": level,
            "should_alert": should_alert,
            "signals": {
                "classifier": {
                    "estimated_attack_probability": p_clf,
                    "predicted_category": predicted_category,
                    "weight": self.weights["classifier"],
                    "contribution": round(self.weights["classifier"] * p_clf, 4)
                },
                "anomaly": {
                    "anomaly_score": s_anom,
                    "weight": self.weights["anomaly"],
                    "contribution": round(self.weights["anomaly"] * s_anom, 4)
                },
                "forecast": {
                    "estimated_future_attack_probability": p_fc,
                    "weight": self.weights["forecast"],
                    "contribution": round(self.weights["forecast"] * p_fc, 4)
                }
            },
            "wording": f"Model-estimated risk level: {level} (Score: {composite_score * 100:.1f}%)"
        }
        return assessment

# Global instance
risk_engine = RiskEngine()
