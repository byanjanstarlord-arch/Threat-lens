"""
Unit Tests for ThreatLens AI Machine Learning Engines & Inference
"""

import pytest
import numpy as np
import pandas as pd
from threatlens.config import settings
from threatlens.ml.registry import registry
from threatlens.ml.risk_engine import RiskEngine

@pytest.fixture(scope="module")
def pipeline():
    """Load active model pipeline once for tests."""
    return registry.load_active_pipeline()

def test_classifier_inference(pipeline):
    """Test attack classifier outputs valid probabilities and classes."""
    clf = pipeline["classifier"]
    label_encoder = pipeline["label_encoder"]
    features = pipeline["clf_features"]
    
    assert len(features) == 69
    assert len(label_encoder.classes_) == 8
    
    # Create sample synthetic flow vector
    dummy_input = np.zeros((1, len(features)), dtype=np.float32)
    probs = clf.predict_proba(dummy_input)[0]
    
    assert len(probs) == 8
    assert np.isclose(np.sum(probs), 1.0, atol=1e-4)
    pred_idx = np.argmax(probs)
    pred_class = label_encoder.classes_[pred_idx]
    assert pred_class in settings.TAXONOMY_CLASSES

def test_anomaly_detector_inference(pipeline):
    """Test Isolation Forest returns normalized [0, 1] anomaly score."""
    anom = pipeline["anomaly_detector"]
    features = pipeline["clf_features"]
    
    dummy_input = np.zeros((2, len(features)), dtype=np.float32)
    scores, is_anomalous = anom.score(dummy_input)
    
    assert len(scores) == 2
    assert len(is_anomalous) == 2
    assert (scores >= 0.0).all() and (scores <= 1.0).all()
    assert set(np.unique(is_anomalous)).issubset({0, 1})

def test_forecaster_inference(pipeline):
    """Test temporal forecaster produces valid horizon attack probability."""
    fc = pipeline["forecaster"]
    fc_features = pipeline["fc_features"]
    
    dummy_input = np.ones((1, len(fc_features)), dtype=np.float32) * 10.0
    prob = float(fc.predict_proba(dummy_input)[0, 1])
    
    assert 0.0 <= prob <= 1.0

def test_shap_explanation(pipeline):
    """Test SHAP returns top-k feature attributions for a flow."""
    explainer = pipeline["explainer"]
    features = pipeline["clf_features"]
    
    dummy_input = np.ones(len(features), dtype=np.float32) * 5.0
    attributions = explainer.explain_flow(dummy_input, top_k=5)
    
    assert len(attributions) == 5
    for attr in attributions:
        assert "feature" in attr
        assert "value" in attr
        assert "shap_value" in attr
        assert attr["impact"] in ["increases_risk", "decreases_risk"]

def test_risk_engine_configurable_evaluation():
    """Test Risk Engine composite score and configurable thresholds."""
    custom_weights = {"classifier": 0.5, "anomaly": 0.2, "forecast": 0.3}
    custom_thresholds = {"LOW": 0.0, "MEDIUM": 0.25, "HIGH": 0.55, "CRITICAL": 0.80}
    
    engine = RiskEngine(weights=custom_weights, thresholds=custom_thresholds)
    
    # Low risk benign flow
    res_low = engine.evaluate_risk(classifier_prob=0.05, anomaly_score=0.1, forecast_prob=0.1)
    assert res_low["risk_level"] == "LOW"
    assert res_low["should_alert"] is False
    assert 0.0 <= res_low["composite_risk_score"] < 0.25
    
    # Critical risk attack flow
    res_crit = engine.evaluate_risk(classifier_prob=0.95, anomaly_score=0.9, forecast_prob=0.85, predicted_category="DDOS")
    assert res_crit["risk_level"] == "CRITICAL"
    assert res_crit["should_alert"] is True
    assert res_crit["composite_risk_score"] >= 0.80
    assert "Model-estimated attack probability" not in res_crit["wording"]  # Must not claim certainty
