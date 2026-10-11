# ThreatLens AI — AI-Based Network Attack Forecasting & Early Warning System
> **"See the Threat Before It Strikes."**

ThreatLens AI is a production-grade cybersecurity intelligence platform that analyzes real network telemetry, detects malicious behavior, identifies attack categories, spots behavioral anomalies, and forecasts the probability of an attack occurring in a future 5-minute time window with measurable warning lead times.

---

## 1. Project Overview
Traditional Intrusion Detection Systems (IDS) are predominantly **reactive**—they generate alerts only after malicious packets have penetrated defenses or while an attack is actively causing disruption. **ThreatLens AI** shifts the cybersecurity paradigm from post-breach detection to **predictive early warning**. By analyzing micro-temporal trends, TCP control flag ratios, flow arrival dynamics, and packet size variances across sliding time windows, ThreatLens AI forecasts impending attacks minutes before full attack onset, giving Security Operations Center (SOC) teams vital lead time to deploy countermeasures.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Data & Pipeline Layer
        RAW["Raw CIC-IDS2017 CSVs (8 sessions, 2.83M rows)"] --> INGEST["Memory-Aware Preprocessing Pipeline"]
        INGEST --> PARQUET["data/processed/clean_flows.parquet"]
        PARQUET --> TRACK_A["Track A: Classification Partition<br/>(Stratified + Duplicate Quarantined)"]
        PARQUET --> TRACK_B["Track B: Forecasting Timeline<br/>(Reconstructed Relative Session Timeline)"]
    end

    subgraph Intelligence Engines
        TRACK_A --> RF["Random Forest Baseline (Macro F1: 0.9719)"]
        TRACK_A --> XGB["XGBoost Multiclass (Macro F1: 0.9895)"]
        TRACK_A --> AD["Isolation Forest (Test ROC-AUC: 0.7305)"]
        TRACK_B --> FC["Temporal Forecaster (F1: 0.8203, Lead Time: 27.2s)"]
        XGB --> SHAP["SHAP TreeExplainer (Feature Attributions)"]
        XGB & AD & FC --> RISK["Multi-Factor Risk Engine"]
    end

    subgraph Storage & Serving
        RISK --> REGISTRY["Versioned Model Registry (models/v1/)"]
        RISK --> DB[("SQLAlchemy Database<br/>SQLite / PostgreSQL")]
        REGISTRY & DB --> API["FastAPI REST Backend (Port 8000)"]
        TRACK_B --> REPLAY["Historical Dataset Replay Engine"]
        REPLAY --> API
    end

    subgraph SOC Dashboard
        API --> UI["Next.js SOC Interface (Zero Fake Data)"]
    end
```

---

## 3. Core Features
- **Zero Fake Data Policy**: Every chart, table, metric, and percentage is computed directly from the real dataset, trained models, or live database.
- **Multiclass Attack Classification**: Distinguishes between 8 canonical taxonomy categories (`BENIGN`, `DOS`, `DDOS`, `PORT_SCAN`, `BRUTE_FORCE`, `WEB_ATTACK`, `BOTNET`, `OTHER_ATTACK`).
- **Unsupervised Behavioral Anomaly Detection**: Isolation Forest trained strictly on benign baseline flows to flag statistical deviation without conflating anomalies with attacks.
- **Temporal Attack Forecasting**: 1-minute sliding window predictor estimating attack occurrence probability in the future 5-minute horizon with empirical warning lead time tracking.
- **Explainable AI (SHAP)**: Feature attributions explaining top features driving each individual prediction.
- **Multi-Factor Risk Engine**: Transparent weighted formula combining classifier, anomaly, and forecast signals.
- **Historical Dataset Replay**: Realistic chronological replay of test session traffic through the production inference pipeline.
- **SOC Alert Queue**: Interactive triage interface to inspect, acknowledge, and resolve alerts.

---

## 4. Technology Stack
- **Backend & Inference**: Python 3.12, FastAPI, Uvicorn, Pydantic V2
- **Machine Learning**: Scikit-Learn, XGBoost, SHAP, Joblib
- **Data Engineering**: Pandas, PyArrow (Apache Parquet), NumPy
- **Persistence Layer**: SQLAlchemy ORM (turnkey SQLite or PostgreSQL via `DATABASE_URL`)
- **Frontend Dashboard**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons, Recharts
- **Testing & QA**: PyTest, HTTPX

---

## 5. Dataset Information
Built and validated on the official **CIC-IDS2017** benchmark dataset:
- **Total Sessions**: 8 files (Monday through Friday captures)
- **Total Physical Size**: 843.65 MB
- **Total Flows**: 2,830,743 flows
- **Feature Dimensionality**: 78 numeric metrics + 1 ground-truth target (`Label`)
- **Distribution**: 80.3% Benign (2,273,097 flows), 19.7% Malicious (557,646 flows across 14 distinct attack types).

---

## 6. Dataset Setup
Ensure raw files are located in the `raw/` directory:
```
ThreatLens/
  raw/
    Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv
    Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv
    Friday-WorkingHours-Morning.pcap_ISCX.csv
    Monday-WorkingHours.pcap_ISCX.csv
    Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv
    Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv
    Tuesday-WorkingHours.pcap_ISCX.csv
    Wednesday-workingHours.pcap_ISCX.csv
```

---

## 7. Installation

### Python Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

## 8. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
- `DATABASE_URL`: `sqlite:///./threatlens.db` (or `postgresql://user:pass@localhost:5432/threatlens`)
- `WINDOW_SIZE_SECONDS`: 60 (1 minute)
- `FORECAST_HORIZON_SECONDS`: 300 (5 minutes)
- `RISK_WEIGHT_CLASSIFIER`: 0.45
- `RISK_WEIGHT_ANOMALY`: 0.25
- `RISK_WEIGHT_FORECAST`: 0.30

---

## 9. Database Setup
ThreatLens AI automatically creates tables on startup via SQLAlchemy ORM.
To run on PostgreSQL:
```bash
export DATABASE_URL="postgresql://postgres:password@localhost:5432/threatlens"
```

---

## 10. Training Pipeline
To execute the complete end-to-end training pipeline sequentially:
```bash
# 1. Ingest raw CSVs, clean, quarantine duplicates, and build dual-track partitions:
python -m threatlens.data.preprocess

# 2. Train all models sequentially, compute SHAP, and register in model registry:
python -m threatlens.ml.train_all
```

Individual training commands:
```bash
python -m threatlens.ml.train_classifier
python -m threatlens.ml.train_anomaly
python -m threatlens.ml.train_forecaster
```

---

## 11. Evaluation & Model Comparison
Display real empirical evaluation metrics across both tracks:
```bash
python -m threatlens.ml.evaluate
```
**Test Results (v1)**:
- **Random Forest Baseline**: Macro F1: `0.9719`, Weighted F1: `0.9970`
- **XGBoost Classifier**: Macro F1: `0.9895`, Weighted F1: `0.9990`, Benign FPR: `0.15%`
- **Isolation Forest**: Test ROC-AUC: `0.7305`, False Alarm Rate: `2.89%`
- **Temporal Forecaster**: Precision: `0.9512`, Recall: `0.7210`, F1: `0.8203`, PR-AUC: `0.9596`
- **Warning Lead Time**: Mean: `27.2 seconds` advance warning before attack onset!
- **Unseen Attack Generalization (Botnet held-out)**: `98.97%` flagged as non-benign threat.

---

## 12. Running the Backend Server
```bash
python -m threatlens.api
# Server runs on http://127.0.0.1:8000
# Interactive Swagger Documentation: http://127.0.0.1:8000/docs
```

---

## 13. Running the Frontend Dashboard
```bash
cd frontend
npm run dev
# Dashboard runs on http://localhost:3000
```

---

## 14. Replay Mode
Replay streams real historical test windows chronologically through production inference:
```bash
# CLI demonstration:
python -m threatlens.replay
```
From the UI: Navigate to `/replay` and click **Start Replay** or **Step 1 Window**.

---

## 15. Live Network Monitoring Status
> [!IMPORTANT]
> **Operational Status Statement:**
> **"Historical CIC-IDS2017 replay is implemented. Live telemetry adapters (Zeek, TShark, Suricata) are future work."**
> 
> ThreatLens AI operates strictly on the CIC-IDS2017 historical benchmark data streamed via the dataset replay engine. Live network packet capture and promiscuous sniffing adapters are planned for subsequent milestones.

---

## 16. API Documentation Summary
| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | GET | Health status and active model version |
| `/api/traffic/summary` | GET | Real flow counters, byte/packet rates, active alerts |
| `/api/traffic/timeline` | GET | Chronological window throughput metrics |
| `/api/predict` | POST | Classifies flow, computes anomaly score, SHAP, and composite risk |
| `/api/forecast` | POST | Estimates attack probability in next 5 minutes |
| `/api/forecast/timeline` | GET | Historical forecast curves & ground-truth verification |
| `/api/attacks` | GET | Incident log with SHAP feature attributions |
| `/api/alerts` | GET | SOC alert queue |
| `/api/alerts/{id}/acknowledge` | PATCH | Acknowledges alert |
| `/api/alerts/{id}/resolve` | PATCH | Resolves alert |
| `/api/models` | GET | Model registry manifest |
| `/api/models/active` | GET | Active model metadata & comparative metrics |
| `/api/replay/start` | POST | Starts chronological dataset replay |
| `/api/replay/stop` | POST | Pauses replay |
| `/api/replay/step` | POST | Steps exactly 1 window |

---

## 17. Explainable AI (SHAP)
ThreatLens AI integrates `shap.TreeExplainer` on the XGBoost classifier. For every flow evaluated, the backend extracts the top-5 feature drivers and their directional impact:
- Example: `Destination Port=21` (+0.82), `min_seg_size_forward=32` (+0.31) $\rightarrow$ Class: `BRUTE_FORCE`.

---

## 18. Forecasting Methodology & Dual Evaluation

### A. Experimental Protocol
1. **Reconstructed Relative Session Timeline**: Monotonically constructed from cumulative flow inter-arrival times and duration.
2. **Backward-Looking Windows**: Windows of size $W=60\text{s}$. Features at $T$ strictly summarize flows completing $\le T$.
3. **Future Horizon Target**: $Y_T = 1$ if any attack flow begins in $(T, T+300\text{s}]$, 0 otherwise.
4. **Decision Threshold Selection**: Frozen at $\tau=0.50$ based on validation set precision objective ($\text{Precision} \ge 0.50$ on Thursday) prior to test evaluation.
5. **Class Prevalence & Baselines**:
   - Train Prevalence: 66.01% (1,606 / 2,433)
   - Validation Prevalence: 42.86% (138 / 322)
   - Test Prevalence: 80.08% (595 / 743)
   - **Trivial Random PR-AUC Baseline:** `0.8008` (Model PR-AUC: `0.9596`, Excess: `+0.1588`)

### B. Window-Level vs Event-Level Metrics
- **Window-Level Metrics (743 test windows):**
  - Precision: **95.12%** | Recall: **72.10%** | F1-Score: **0.8203** | ROC-AUC: **0.8350**
  - True Positives: 429 | False Positives: 22 | True Negatives: 126 | False Negatives: 166
  - Window-Level Lead Time: Mean 27.2s | Median 0.23s
- **Warning Separation:**
  - **Ongoing-Campaign Warnings:** **347 (80.89%)** — Occur inside active multi-minute campaigns; lead times are sub-second (<1s) as traffic continuously crosses window boundaries.
  - **Genuine Pre-Onset Warnings:** **82 (19.11%)** — Triggered strictly *before* the first malicious packet of an attack campaign strikes.
- **Event-Level Campaign Metrics (27 Attack Campaigns):**
  - Total Campaigns: 27 (19 DDoS, 6 PortScan, 2 Botnet)
  - Campaigns with Pre-Onset Warning: **20 / 27 (74.07%)**
  - **Genuine Onset Lead Time:**
    - Mean: **236.62 seconds (~3.94 minutes)**
    - Median: **237.97 seconds (~3.97 minutes)**
    - Range: 181.07s to 289.47s (100% of onset warnings provide $> 120\text{s}$ advance notice)

---

## 19. Limitations
- Encrypted payloads: Models rely strictly on flow-level statistical metrics rather than deep packet payload inspection.
- Fixed temporal window size: 1-minute window size is optimized for flow volume in enterprise captures; microsecond flash attacks may require smaller sub-second windows.

---

## 20. Security Considerations
- Defensive tool: Does not include offensive attack automation or exploit capabilities.
- Strict input sanitization and Pydantic validation on all REST endpoints.
- No secrets or credentials hardcoded or stored in Git.

---

## 21. Automated Testing
Execute the complete test suite:
```bash
pytest tests/ -v
```
Verified tests:
- `tests/test_data_pipeline.py`: Header normalization, NaN/Inf imputation, preprocessor persistence, partition integrity.
- `tests/test_leakage.py`: Cross-split duplicate quarantine, backward-only rolling feature independence.
- `tests/test_ml_engine.py`: Classifier, Anomaly detector, Forecaster, SHAP explainer, Risk engine.
- `tests/test_api.py`: FastAPI endpoints, replay step, alert workflow.

---

## 22. Troubleshooting
- **Missing Parquet files**: Run `python -m threatlens.data.preprocess` to generate clean partitions.
- **Model artifacts missing**: Run `python -m threatlens.ml.train_all` to train and register model version `v1`.
- **Port 8000 in use**: Specify alternative port: `uvicorn threatlens.backend.app:app --port 8001`.
