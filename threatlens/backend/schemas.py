"""
ThreatLens AI - Pydantic Request & Response Schemas
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PredictRequest(BaseModel):
    features: Dict[str, float] = Field(..., description="Map of network flow features")

class SHAPFeature(BaseModel):
    feature: str
    value: float
    shap_value: float
    impact: str

class PredictResponse(BaseModel):
    model_version: str
    predicted_class: str
    confidence: float
    anomaly_score: float
    is_anomalous: bool
    composite_risk_score: float
    risk_level: str
    should_alert: bool
    risk_assessment: Dict[str, Any]
    shap_top_features: List[SHAPFeature]

class ForecastRequest(BaseModel):
    window_features: Dict[str, float] = Field(..., description="Window telemetry features")

class ForecastResponse(BaseModel):
    model_version: str
    forecast_horizon_seconds: int
    forecast_attack_probability: float
    risk_level: str
    confidence_wording: str
    predicted_category: str

class AlertOut(BaseModel):
    id: int
    timestamp: datetime
    alert_type: str
    severity: str
    title: str
    message: str
    status: str
    source_event_type: str

class TrafficSummary(BaseModel):
    total_flows_analyzed: int
    total_attacks_detected: int
    active_alerts_count: int
    current_risk_score: float
    current_risk_level: str
    average_byte_rate: float
    average_packet_rate: float

class ReplayStatus(BaseModel):
    is_running: bool
    current_window_index: int
    total_windows: int
    speed_multiplier: float
    mode: str = "Dataset Replay Mode"
