"""
ThreatLens AI - FastAPI Application
Main entry point for ThreatLens cybersecurity backend services.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from threatlens.config import settings
from threatlens.backend.database import engine, Base, get_db
from threatlens.backend.models_db import (
    TrafficWindow, Prediction, ForecastPrediction, AttackEvent, Alert, ModelRecord
)
from threatlens.backend.schemas import (
    PredictRequest, PredictResponse, ForecastRequest, ForecastResponse,
    AlertOut, TrafficSummary, ReplayStatus
)
from threatlens.backend.services.prediction_service import prediction_service
from threatlens.backend.services.forecasting_service import forecasting_service
from threatlens.backend.services.replay_service import replay_engine
from threatlens.ml.registry import registry

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ThreatLens AI API",
    description="AI-Based Network Attack Forecasting & Early Warning System API",
    version=settings.APP_VERSION
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Load active model pipeline once at startup."""
    try:
        registry.load_active_pipeline()
    except Exception as e:
        print(f"[Startup Warning] Could not preload active pipeline: {e}")

@app.get("/api/health")
def get_health():
    manifest = registry.get_registry_manifest()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "active_model_version": manifest.get("active_version", "v1"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# -----------------------------------------------------------------------------
# Traffic Telemetry Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/traffic/summary")
def get_traffic_summary(db: Session = Depends(get_db)):
    total_flows = db.query(Prediction).count()
    total_attacks = db.query(AttackEvent).count()
    active_alerts = db.query(Alert).filter(Alert.status != "RESOLVED").count()
    
    # Compute current risk from latest prediction
    latest_pred = db.query(Prediction).order_by(desc(Prediction.id)).first()
    curr_risk = float(latest_pred.composite_risk) if latest_pred else 0.0
    curr_level = latest_pred.risk_level if latest_pred else "NO DATA"
    
    # Average byte & packet rate from recent windows
    avg_rates = db.query(
        func.avg(TrafficWindow.byte_rate),
        func.avg(TrafficWindow.packet_rate)
    ).first()
    
    avg_byte_rate = float(avg_rates[0]) if avg_rates and avg_rates[0] else 0.0
    avg_pkt_rate = float(avg_rates[1]) if avg_rates and avg_rates[1] else 0.0
    
    return {
        "total_flows_analyzed": total_flows,
        "total_attacks_detected": total_attacks,
        "active_alerts_count": active_alerts,
        "current_risk_score": curr_risk,
        "current_risk_level": curr_level,
        "average_byte_rate": avg_byte_rate,
        "average_packet_rate": avg_pkt_rate
    }

@app.get("/api/traffic/timeline")
def get_traffic_timeline(limit: int = 50, db: Session = Depends(get_db)):
    windows = db.query(TrafficWindow).order_by(desc(TrafficWindow.id)).limit(limit).all()
    # Return chronologically
    return [
        {
            "id": w.id,
            "window_id": w.window_id,
            "start_time_sec": w.start_time_sec,
            "end_time_sec": w.end_time_sec,
            "flow_count": w.flow_count,
            "byte_rate": w.byte_rate,
            "packet_rate": w.packet_rate,
            "syn_flag_count": w.syn_flag_count,
            "ack_flag_count": w.ack_flag_count
        }
        for w in reversed(windows)
    ]

# -----------------------------------------------------------------------------
# Prediction & Inference Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/predict", response_model=PredictResponse)
def post_predict(req: PredictRequest, db: Session = Depends(get_db)):
    return prediction_service.predict_single_flow(req.features, db)

# -----------------------------------------------------------------------------
# Forecasting Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/forecast", response_model=ForecastResponse)
def post_forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    return forecasting_service.predict_window_forecast(req.window_features, db)

@app.get("/api/forecast/timeline")
def get_forecast_timeline(limit: int = 50, db: Session = Depends(get_db)):
    fcs = db.query(ForecastPrediction).order_by(desc(ForecastPrediction.id)).limit(limit).all()
    return [
        {
            "id": f.id,
            "timestamp": f.timestamp.isoformat() if f.timestamp else None,
            "window_id": f.window_id,
            "model_version": f.model_version,
            "horizon_seconds": f.horizon_seconds,
            "forecast_attack_prob": f.forecast_attack_prob,
            "predicted_category": f.predicted_category,
            "risk_level": f.risk_level,
            "observed_outcome": f.observed_outcome,
            "actual_attack_occurred": f.actual_attack_occurred,
            "lead_time_seconds": f.lead_time_seconds
        }
        for f in reversed(fcs)
    ]

# -----------------------------------------------------------------------------
# Attacks & Incidents Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/attacks")
def get_attacks(limit: int = 50, db: Session = Depends(get_db)):
    attacks = db.query(AttackEvent).order_by(desc(AttackEvent.id)).limit(limit).all()
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "attack_type": a.attack_type,
            "confidence": a.confidence,
            "risk_level": a.risk_level,
            "destination_port": a.destination_port,
            "details": a.details
        }
        for a in attacks
    ]

# -----------------------------------------------------------------------------
# Alert Management Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/alerts")
def get_alerts(status_filter: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(Alert)
    if status_filter:
        q = q.filter(Alert.status == status_filter.upper())
    alerts = q.order_by(desc(Alert.id)).limit(limit).all()
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "status": a.status,
            "source_event_type": a.source_event_type
        }
        for a in alerts
    ]

@app.patch("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "SUCCESS", "alert_id": alert_id, "new_status": "ACKNOWLEDGED"}

@app.patch("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "SUCCESS", "alert_id": alert_id, "new_status": "RESOLVED"}

# -----------------------------------------------------------------------------
# Model Registry & Metrics Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/models")
def get_model_registry():
    return registry.get_registry_manifest()

@app.get("/api/models/active")
def get_active_model():
    manifest = registry.get_registry_manifest()
    act_ver = manifest.get("active_version", "v1")
    return manifest.get("versions", {}).get(act_ver, {})

@app.get("/api/models/{version}/metrics")
def get_model_metrics(version: str):
    manifest = registry.get_registry_manifest()
    v_data = manifest.get("versions", {}).get(version)
    if not v_data:
        raise HTTPException(status_code=404, detail=f"Model version {version} not found")
    return v_data.get("metrics", {})

# -----------------------------------------------------------------------------
# Analytics Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/analytics/attack-distribution")
def get_attack_distribution(db: Session = Depends(get_db)):
    dist = db.query(AttackEvent.attack_type, func.count(AttackEvent.id)).group_by(AttackEvent.attack_type).all()
    return [{"attack_type": d[0], "count": d[1]} for d in dist]

@app.get("/api/analytics/risk-history")
def get_risk_history(limit: int = 50, db: Session = Depends(get_db)):
    preds = db.query(Prediction.id, Prediction.timestamp, Prediction.composite_risk, Prediction.risk_level).order_by(desc(Prediction.id)).limit(limit).all()
    return [
        {
            "id": p.id,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "composite_risk": p.composite_risk,
            "risk_level": p.risk_level
        }
        for p in reversed(preds)
    ]

# -----------------------------------------------------------------------------
# Dataset Replay Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/replay/start")
def start_replay(speed: float = Query(1.0, ge=0.1, le=20.0)):
    replay_engine.start(speed=speed)
    return {"status": "SUCCESS", "message": "Dataset replay started", "speed": speed}

@app.post("/api/replay/stop")
def stop_replay():
    replay_engine.stop()
    return {"status": "SUCCESS", "message": "Dataset replay stopped"}

@app.post("/api/replay/step")
def step_replay():
    res = replay_engine.step_single_window()
    return res

@app.post("/api/replay/reset")
def reset_replay():
    replay_engine.reset()
    return {"status": "SUCCESS", "message": "Dataset replay reset"}

@app.get("/api/replay/status", response_model=ReplayStatus)
def get_replay_status():
    return replay_engine.get_status()
