"""
ThreatLens AI - Database Models (SQLAlchemy ORM)
Unified schema compatible with both SQLite and PostgreSQL.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
)
from threatlens.backend.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class TrafficWindow(Base):
    __tablename__ = "traffic_windows"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    window_id = Column(Integer, index=True)
    start_time_sec = Column(Float, index=True)
    end_time_sec = Column(Float, index=True)
    flow_count = Column(Integer)
    byte_rate = Column(Float)
    packet_rate = Column(Float)
    syn_flag_count = Column(Float)
    ack_flag_count = Column(Float)
    created_at = Column(DateTime, default=utcnow)

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    flow_index = Column(Integer, nullable=True)
    model_version = Column(String(50), index=True)
    predicted_class = Column(String(50), index=True)
    confidence = Column(Float)
    anomaly_score = Column(Float)
    is_anomalous = Column(Boolean)
    composite_risk = Column(Float, index=True)
    risk_level = Column(String(20), index=True)
    shap_features = Column(JSON, nullable=True)

class ForecastPrediction(Base):
    __tablename__ = "forecast_predictions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    window_id = Column(Integer, index=True)
    model_version = Column(String(50))
    horizon_seconds = Column(Integer)
    forecast_attack_prob = Column(Float)
    predicted_category = Column(String(50))
    risk_level = Column(String(20))
    # Filled when future horizon elapses
    observed_outcome = Column(String(50), nullable=True)
    actual_attack_occurred = Column(Boolean, nullable=True)
    lead_time_seconds = Column(Float, nullable=True)

class AttackEvent(Base):
    __tablename__ = "attack_events"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    attack_type = Column(String(50), index=True)
    confidence = Column(Float)
    risk_level = Column(String(20))
    model_version = Column(String(50))
    source_port = Column(Integer, nullable=True)
    destination_port = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    alert_type = Column(String(100), index=True)
    severity = Column(String(20), index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255))
    message = Column(Text)
    source_event_type = Column(String(50))     # PREDICTION, FORECAST, ANOMALY
    source_event_id = Column(Integer, nullable=True)
    status = Column(String(20), default="UNRESOLVED", index=True) # UNRESOLVED, ACKNOWLEDGED, RESOLVED
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

class ModelRecord(Base):
    __tablename__ = "model_versions"
    
    version = Column(String(50), primary_key=True)
    registered_at = Column(DateTime, default=utcnow)
    status = Column(String(20), default="active")
    metrics = Column(JSON)
    artifacts_dir = Column(String(255))
