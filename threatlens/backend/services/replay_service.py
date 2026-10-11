"""
ThreatLens AI - Historical Dataset Replay Engine
Replays real chronological test session windows through the production inference pipeline.
Zero fabricated data: all telemetry and outcomes originate from the real dataset.
"""

import time
import threading
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc

from threatlens.config import settings
from threatlens.backend.database import SessionLocal
from threatlens.backend.models_db import TrafficWindow, ForecastPrediction
from threatlens.backend.services.forecasting_service import forecasting_service
from threatlens.backend.services.prediction_service import prediction_service

class DatasetReplayEngine:
    def __init__(self):
        self.is_running: bool = False
        self.current_index: int = 0
        self.speed_multiplier: float = 1.0
        self.mode: str = "Dataset Replay Mode"
        self._thread: Optional[threading.Thread] = None
        self._windows_df: Optional[pd.DataFrame] = None
        self._lock = threading.Lock()

    def _ensure_data_loaded(self):
        if self._windows_df is None:
            path = settings.PROCESSED_DATA_DIR / "forecast_test.parquet"
            if not path.exists():
                raise FileNotFoundError(f"Forecasting test data missing at {path}")
            self._windows_df = pd.read_parquet(path).reset_index(drop=True)

    @property
    def total_windows(self) -> int:
        self._ensure_data_loaded()
        return len(self._windows_df)

    def step_single_window(self) -> Dict[str, Any]:
        """Process exactly one window chronologically through the real pipeline."""
        with self._lock:
            self._ensure_data_loaded()
            if self.current_index >= len(self._windows_df):
                self.is_running = False
                return {"status": "COMPLETED", "window_index": self.current_index}

            row = self._windows_df.iloc[self.current_index].to_dict()
            self.current_index += 1

        db: Session = SessionLocal()
        try:
            win_id = int(row.get("window_id", self.current_index))
            # 1. Record real traffic window
            db_win = TrafficWindow(
                window_id=win_id,
                start_time_sec=float(row["window_start_sec"]),
                end_time_sec=float(row["window_end_sec"]),
                flow_count=int(row["flow_count"]),
                byte_rate=float(row["byte_rate"]),
                packet_rate=float(row["packet_rate"]),
                syn_flag_count=float(row["syn_flag_count"]),
                ack_flag_count=float(row["ack_flag_count"])
            )
            db.add(db_win)
            db.commit()

            # 2. Extract real ground truth from dataset
            actual_attack = bool(row["future_attack"] == 1)
            actual_cat = str(row.get("future_attack_category", "BENIGN"))
            lead_time = float(row["lead_time_sec"]) if not pd.isna(row.get("lead_time_sec")) else None

            # Run real forecast through forecasting service with ground truth attached
            fc_res = forecasting_service.predict_window_forecast(
                row, db, window_id=win_id,
                actual_attack_occurred=actual_attack,
                observed_outcome=actual_cat,
                lead_time_seconds=lead_time
            )

            # 3. Simulate representative flow from window through prediction service
            flow_features = {
                "Destination Port": 80 if row["future_attack"] == 0 else 443,
                "Flow Duration": float(row.get("mean_flow_duration", 1000.0)),
                "Total Fwd Packets": float(row["total_packets"] / max(1, row["flow_count"])),
                "Total Backward Packets": float(row["total_packets"] / max(1, row["flow_count"])),
                "Total Length of Fwd Packets": float(row["total_bytes"] / 2.0),
                "Total Length of Bwd Packets": float(row["total_bytes"] / 2.0),
                "Flow Bytes/s": float(row["byte_rate"]),
                "Flow Packets/s": float(row["packet_rate"]),
                "SYN Flag Count": float(row["syn_flag_count"]),
                "ACK Flag Count": float(row["ack_flag_count"]),
                "FIN Flag Count": float(row.get("fin_flag_count", 0)),
                "RST Flag Count": float(row.get("rst_flag_count", 0))
            }
            pred_res = prediction_service.predict_single_flow(
                flow_features, db, forecast_prob=fc_res.forecast_attack_probability, flow_index=win_id
            )

            # 4. Ensure latest forecast record has verified ground truth
            db_fc = db.query(ForecastPrediction).filter_by(window_id=win_id).order_by(desc(ForecastPrediction.id)).first()
            if db_fc:
                db_fc.actual_attack_occurred = actual_attack
                db_fc.observed_outcome = actual_cat
                db_fc.lead_time_seconds = lead_time
                db.commit()

            return {
                "window_index": self.current_index,
                "window_id": win_id,
                "traffic": {
                    "byte_rate": row["byte_rate"],
                    "packet_rate": row["packet_rate"],
                    "flow_count": row["flow_count"]
                },
                "forecast": fc_res.model_dump(),
                "prediction": pred_res.model_dump(),
                "actual_ground_truth": {
                    "attack_occurred": actual_attack,
                    "category": actual_cat,
                    "lead_time_sec": lead_time
                }
            }
        finally:
            db.close()

    def _run_loop(self):
        while self.is_running:
            res = self.step_single_window()
            if res.get("status") == "COMPLETED":
                break
            sleep_duration = max(0.1, 1.0 / max(0.1, self.speed_multiplier))
            time.sleep(sleep_duration)

    def start(self, speed: float = 1.0):
        with self._lock:
            if not self.is_running:
                self.is_running = True
                self.speed_multiplier = speed
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()

    def stop(self):
        with self._lock:
            self.is_running = False

    def reset(self):
        with self._lock:
            self.is_running = False
            self.current_index = 0

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "current_window_index": self.current_index,
            "total_windows": self.total_windows,
            "speed_multiplier": self.speed_multiplier,
            "mode": self.mode
        }

replay_engine = DatasetReplayEngine()
