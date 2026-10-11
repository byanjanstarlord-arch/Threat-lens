"""
ThreatLens AI - End-to-End Data Preprocessing & Partitioning Pipeline
Generates both:
Track A: Attack Classification Track (Stratified + Duplicate Quarantined)
Track B: Temporal Forecasting Track (Reconstructed Relative Session Timeline + Chronological Splits)
"""

import os
import gc
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from threatlens.config import settings
from threatlens.data.clean import FlowPreprocessor, clean_csv_chunk, normalize_label_string
from threatlens.data.leakage import quarantine_duplicates_across_splits, verify_no_cross_split_contamination
from threatlens.data.timeline import construct_relative_session_timeline, aggregate_time_windows

def process_raw_dataset_to_clean_parquet(
    raw_dir: Path = settings.RAW_DATA_DIR,
    interim_dir: Path = settings.INTERIM_DATA_DIR,
    chunk_size: int = settings.CHUNK_SIZE
) -> Path:
    """
    Ingest all 8 raw CSVs chunk-by-chunk, clean, downcast, and persist as interim Parquet files.
    Ensures memory awareness for 16GB RAM limit.
    """
    interim_dir.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(list(raw_dir.glob("*.csv")))
    print(f"[Ingestion] Found {len(raw_files)} CSV files in {raw_dir}")
    
    combined_parquet_path = interim_dir / "all_flows_clean.parquet"
    if combined_parquet_path.exists():
        print(f"[Ingestion] Clean parquet already exists at {combined_parquet_path}")
        return combined_parquet_path

    writer = None
    total_processed_rows = 0
    start_time = time.time()

    for fpath in raw_files:
        print(f"[Ingestion] Processing file: {fpath.name}")
        session_name = fpath.stem.split(".")[0]
        
        # Read in chunks to respect 16GB RAM constraints
        chunk_iter = pd.read_csv(
            fpath,
            chunksize=chunk_size,
            encoding="latin1",
            low_memory=False
        )
        
        for chunk in chunk_iter:
            features, labels = clean_csv_chunk(chunk)
            features["Label"] = labels
            features["session"] = session_name
            
            # Downcast to float32 where appropriate
            for col in features.select_dtypes(include=["float64"]).columns:
                features[col] = features[col].astype(np.float32)
                
            table = pa.Table.from_pandas(features, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(combined_parquet_path, table.schema, compression="snappy")
            writer.write_table(table)
            total_processed_rows += len(features)
            
        gc.collect()

    if writer:
        writer.close()

    elapsed = time.time() - start_time
    print(f"[Ingestion] Completed in {elapsed:.1f}s. Total rows written: {total_processed_rows:,}")
    return combined_parquet_path

def build_dual_track_partitions(
    clean_parquet_path: Path,
    processed_dir: Path = settings.PROCESSED_DATA_DIR,
    max_clf_samples: int = 500000
) -> Dict[str, Any]:
    """
    Build dual evaluation tracks:
    Track A: Leakage-aware Stratified Classification Partitions with duplicate quarantine
    Track B: Reconstructed Relative Session Timeline for 1-minute windowed Forecasting
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    print("\n[Pipeline] Building Dual Evaluation Tracks...")

    # Load clean dataset
    df = pd.read_parquet(clean_parquet_path)
    print(f"[Pipeline] Loaded {len(df):,} total clean flows.")

    # -------------------------------------------------------------------------
    # TRACK A: Attack Classification Track
    # -------------------------------------------------------------------------
    print("\n--- Track A: Attack Classification Track ---")
    
    # Balance classes for classification track so rare attacks have adequate representation
    # Keep all attacks up to 100,000 per class, sample benign down to balance
    clf_dfs = []
    for cls_name in settings.TAXONOMY_CLASSES:
        cls_sub = df[df["Label"] == cls_name]
        cnt = len(cls_sub)
        if cnt > 0:
            sample_n = min(cnt, 50000 if cls_name == "BENIGN" else 40000)
            clf_dfs.append(cls_sub.sample(n=sample_n, random_state=42) if cnt > sample_n else cls_sub)
            print(f"  - Class {cls_name}: {cnt:,} available -> {min(cnt, sample_n):,} selected")

    df_clf = pd.concat(clf_dfs, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    # 70% Train, 15% Val, 15% Test stratified by Label
    feature_cols = [c for c in df_clf.columns if c not in ["Label", "session", "rel_start_sec", "rel_end_sec"]]
    
    train_parts, val_parts, test_parts = [], [], []
    for cls_name in settings.TAXONOMY_CLASSES:
        cls_subset = df_clf[df_clf["Label"] == cls_name]
        n_cls = len(cls_subset)
        if n_cls == 0:
            continue
        n_train = int(0.70 * n_cls)
        n_val = int(0.15 * n_cls)
        
        train_parts.append(cls_subset.iloc[:n_train])
        val_parts.append(cls_subset.iloc[n_train:n_train+n_val])
        test_parts.append(cls_subset.iloc[n_train+n_val:])

    train_raw = pd.concat(train_parts, ignore_index=True)
    val_raw = pd.concat(val_parts, ignore_index=True)
    test_raw = pd.concat(test_parts, ignore_index=True)

    # Perform duplicate quarantine: remove duplicate vectors crossing boundaries
    clf_train, clf_val, clf_test, audit_clf = quarantine_duplicates_across_splits(
        train_raw, val_raw, test_raw, feature_cols
    )
    
    # Fit FlowPreprocessor strictly on Training data
    preprocessor = FlowPreprocessor()
    preprocessor.fit(clf_train[feature_cols])
    preprocessor.save(settings.MODELS_DIR / "preprocessor.joblib")
    print(f"[Track A] Fitted and saved FlowPreprocessor with {len(preprocessor.feature_columns)} features.")

    # Apply preprocessor to get clean numeric matrices
    clf_train_x = preprocessor.transform(clf_train)
    clf_train_x["Label"] = clf_train["Label"].values
    clf_val_x = preprocessor.transform(clf_val)
    clf_val_x["Label"] = clf_val["Label"].values
    clf_test_x = preprocessor.transform(clf_test)
    clf_test_x["Label"] = clf_test["Label"].values

    clf_train_x.to_parquet(processed_dir / "clf_train.parquet", index=False)
    clf_val_x.to_parquet(processed_dir / "clf_val.parquet", index=False)
    clf_test_x.to_parquet(processed_dir / "clf_test.parquet", index=False)

    print(f"[Track A] Partitions saved: Train={len(clf_train_x):,}, Val={len(clf_val_x):,}, Test={len(clf_test_x):,}")
    print(f"[Track A] Duplicate Quarantine: Val quarantined={audit_clf['val_quarantined_duplicates']}, Test quarantined={audit_clf['test_quarantined_duplicates']}")

    # -------------------------------------------------------------------------
    # TRACK B: Temporal Forecasting Track
    # -------------------------------------------------------------------------
    print("\n--- Track B: Temporal Forecasting Track ---")
    # Chronological session split:
    # Train: Monday, Tuesday, Wednesday
    # Val: Thursday Morning & Afternoon
    # Test: Friday Morning & Afternoon
    train_sessions = [s for s in df["session"].unique() if any(d in s.lower() for d in ["monday", "tuesday", "wednesday"])]
    val_sessions = [s for s in df["session"].unique() if "thursday" in s.lower()]
    test_sessions = [s for s in df["session"].unique() if "friday" in s.lower()]

    print(f"[Track B] Train sessions: {train_sessions}")
    print(f"[Track B] Val sessions: {val_sessions}")
    print(f"[Track B] Test sessions: {test_sessions}")

    # Build Reconstructed Relative Session Timeline per partition
    def build_windowed_partition(session_names: list, name: str) -> pd.DataFrame:
        sub_df = df[df["session"].isin(session_names)].copy()
        if len(sub_df) == 0:
            return pd.DataFrame()
        sub_timeline = construct_relative_session_timeline(sub_df)
        windows = aggregate_time_windows(
            sub_timeline,
            window_size_sec=settings.WINDOW_SIZE_SECONDS,
            horizon_sec=settings.FORECAST_HORIZON_SECONDS
        )
        print(f"[Track B] {name}: {len(sub_df):,} flows -> {len(windows):,} 1-minute windows (Attacks in horizon: {windows['future_attack'].sum()})")
        return windows

    win_train = build_windowed_partition(train_sessions, "Train")
    win_val = build_windowed_partition(val_sessions, "Validation")
    win_test = build_windowed_partition(test_sessions, "Test")

    win_train.to_parquet(processed_dir / "forecast_train.parquet", index=False)
    win_val.to_parquet(processed_dir / "forecast_val.parquet", index=False)
    win_test.to_parquet(processed_dir / "forecast_test.parquet", index=False)

    report = {
        "status": "SUCCESS",
        "total_clean_flows": len(df),
        "track_a_classification": {
            "train_rows": len(clf_train_x),
            "val_rows": len(clf_val_x),
            "test_rows": len(clf_test_x),
            "feature_count": len(preprocessor.feature_columns),
            "quarantined_duplicates": audit_clf
        },
        "track_b_forecasting": {
            "window_size_sec": settings.WINDOW_SIZE_SECONDS,
            "horizon_sec": settings.FORECAST_HORIZON_SECONDS,
            "train_windows": len(win_train),
            "train_future_attack_windows": int(win_train["future_attack"].sum()) if len(win_train) else 0,
            "val_windows": len(win_val),
            "val_future_attack_windows": int(win_val["future_attack"].sum()) if len(win_val) else 0,
            "test_windows": len(win_test),
            "test_future_attack_windows": int(win_test["future_attack"].sum()) if len(win_test) else 0
        }
    }

    report_path = settings.REPORTS_DIR / "data_quality_report.json"
    with open(report_path, "w") as fp:
        json.dump(report, fp, indent=2)

    print(f"\n[Pipeline] Preprocessing and data quality report saved to {report_path}")
    return report

if __name__ == "__main__":
    parquet_path = process_raw_dataset_to_clean_parquet()
    build_dual_track_partitions(parquet_path)
