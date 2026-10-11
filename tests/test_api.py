"""
Integration Tests for ThreatLens AI FastAPI Backend & Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from threatlens.backend.app import app
from threatlens.backend.database import SessionLocal, Base, engine

client = TestClient(app)

def test_api_health():
    """Verify /api/health endpoint returns 200 and valid active model version."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["active_model_version"] == "v1"

def test_api_traffic_summary():
    """Verify /api/traffic/summary returns numeric counters."""
    res = client.get("/api/traffic/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_flows_analyzed" in data
    assert "current_risk_score" in data

def test_api_predict():
    """Verify /api/predict accepts features, runs model, and returns SHAP and Risk."""
    payload = {
        "features": {
            "Destination Port": 80,
            "Flow Duration": 120000,
            "Total Fwd Packets": 10,
            "Total Backward Packets": 8,
            "Flow Bytes/s": 450.0,
            "Flow Packets/s": 2.0,
            "SYN Flag Count": 1,
            "ACK Flag Count": 1
        }
    }
    res = client.post("/api/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["model_version"] == "v1"
    assert "predicted_class" in data
    assert "confidence" in data
    assert "composite_risk_score" in data
    assert "shap_top_features" in data
    assert len(data["shap_top_features"]) == 5

def test_api_forecast():
    """Verify /api/forecast returns horizon attack probability and wording."""
    payload = {
        "window_features": {
            "flow_count": 50,
            "total_bytes": 100000,
            "total_packets": 200,
            "byte_rate": 1666.0,
            "packet_rate": 3.33,
            "syn_flag_count": 10,
            "ack_flag_count": 15,
            "fin_flag_count": 2,
            "rst_flag_count": 0,
            "mean_flow_duration": 50000,
            "rolling_mean_flow_count_3": 45,
            "rolling_mean_byte_rate_3": 1500.0,
            "rolling_max_packet_rate_3": 5.0,
            "flow_growth_rate": 0.1
        }
    }
    res = client.post("/api/forecast", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["model_version"] == "v1"
    assert 0.0 <= data["forecast_attack_probability"] <= 1.0
    assert "Model-estimated attack probability" in data["confidence_wording"]

def test_api_replay_step():
    """Verify /api/replay/step executes a real window through the inference pipeline."""
    res = client.post("/api/replay/step")
    assert res.status_code == 200
    data = res.json()
    assert "window_index" in data
    assert "traffic" in data
    assert "forecast" in data
    assert "prediction" in data

def test_api_models():
    """Verify /api/models returns registered model versions."""
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()
    assert "versions" in data
    assert "v1" in data["versions"]

def test_api_alerts_workflow():
    """Verify alert listing, acknowledgement, and resolution."""
    # List alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    
    if len(alerts) > 0:
        alert_id = alerts[0]["id"]
        # Acknowledge
        ack_res = client.patch(f"/api/alerts/{alert_id}/acknowledge")
        assert ack_res.status_code == 200
        assert ack_res.json()["new_status"] == "ACKNOWLEDGED"
        
        # Resolve
        res_res = client.patch(f"/api/alerts/{alert_id}/resolve")
        assert res_res.status_code == 200
        assert res_res.json()["new_status"] == "RESOLVED"
