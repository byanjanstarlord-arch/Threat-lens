"""
ThreatLens AI - CLI Dataset Inspection Tool
python -m threatlens.data.inspect
"""

import sys
import json
from pathlib import Path
from threatlens.config import settings

def main():
    print("=" * 60)
    print("THREATLENS AI - DATASET INSPECTION")
    print("=" * 60)
    raw_files = sorted(list(settings.RAW_DATA_DIR.glob("*.csv")))
    print(f"Raw Directory: {settings.RAW_DATA_DIR}")
    print(f"Discovered Files: {len(raw_files)}")
    for f in raw_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.2f} MB)")
        
    dqr_path = settings.REPORTS_DIR / "data_quality_report.json"
    if dqr_path.exists():
        with open(dqr_path, "r") as fp:
            dqr = json.load(fp)
        print("\nClean Ingestion Summary:")
        print(f"  Total Clean Flows: {dqr.get('total_clean_flows', 0):,}")
        print(f"  Track A (Classification) Partitions: Train={dqr['track_a_classification']['train_rows']:,}, Val={dqr['track_a_classification']['val_rows']:,}, Test={dqr['track_a_classification']['test_rows']:,}")
        print(f"  Track B (Forecasting) Windows: Train={dqr['track_b_forecasting']['train_windows']}, Val={dqr['track_b_forecasting']['val_windows']}, Test={dqr['track_b_forecasting']['test_windows']}")
    else:
        print("\nData quality report not found. Run 'python -m threatlens.data.preprocess' to generate.")

if __name__ == "__main__":
    main()
