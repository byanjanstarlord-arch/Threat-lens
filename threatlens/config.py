"""
ThreatLens AI - Central Configuration Module
"""

import os
from pathlib import Path
from typing import Dict
from pydantic import BaseModel, Field

# Base Directory of ThreatLens
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    # Application Info
    APP_NAME: str = "ThreatLens AI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Storage Paths
    RAW_DATA_DIR: Path = Path(os.getenv("RAW_DATA_DIR", str(BASE_DIR / "raw")))
    DATA_DIR: Path = BASE_DIR / "data"
    INTERIM_DATA_DIR: Path = BASE_DIR / "data" / "interim"
    PROCESSED_DATA_DIR: Path = BASE_DIR / "data" / "processed"
    MODELS_DIR: Path = BASE_DIR / "models"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'threatlens.db'}")
    
    # Temporal Window Configuration (for Forecasting)
    # Timeline designation: Reconstructed Relative Session Timeline
    WINDOW_SIZE_SECONDS: int = int(os.getenv("WINDOW_SIZE_SECONDS", "60"))       # 1 minute window
    FORECAST_HORIZON_SECONDS: int = int(os.getenv("FORECAST_HORIZON_SECONDS", "300")) # 5 minute horizon
    
    # Risk Engine Configuration (Weights & Thresholds must be configurable)
    RISK_WEIGHTS: Dict[str, float] = {
        "classifier": float(os.getenv("RISK_WEIGHT_CLASSIFIER", "0.45")),
        "anomaly": float(os.getenv("RISK_WEIGHT_ANOMALY", "0.25")),
        "forecast": float(os.getenv("RISK_WEIGHT_FORECAST", "0.30"))
    }
    
    RISK_THRESHOLDS: Dict[str, float] = {
        "LOW": float(os.getenv("RISK_THRESH_LOW", "0.0")),
        "MEDIUM": float(os.getenv("RISK_THRESH_MEDIUM", "0.30")),
        "HIGH": float(os.getenv("RISK_THRESH_HIGH", "0.60")),
        "CRITICAL": float(os.getenv("RISK_THRESH_CRITICAL", "0.85"))
    }
    
    # Hardware & Performance Configuration (Intel i5-13420H / 16GB RAM)
    N_JOBS: int = int(os.getenv("N_JOBS", "4"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "50000"))
    REPLAY_SPEED: float = float(os.getenv("REPLAY_SPEED", "1.0"))
    SHAP_SAMPLE_SIZE: int = int(os.getenv("SHAP_SAMPLE_SIZE", "500"))
    
    # Taxonomy Definition
    TAXONOMY_CLASSES: list[str] = [
        "BENIGN",
        "DOS",
        "PORT_SCAN",
        "DDOS",
        "BRUTE_FORCE",
        "WEB_ATTACK",
        "BOTNET",
        "OTHER_ATTACK"
    ]

# Global singleton
settings = Settings()

# Ensure directories exist
for d in [settings.DATA_DIR, settings.INTERIM_DATA_DIR, settings.PROCESSED_DATA_DIR, settings.MODELS_DIR, settings.REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
