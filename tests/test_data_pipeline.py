"""
Unit Tests for ThreatLens Data Cleaning & Preprocessing Pipeline
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile

from threatlens.data.clean import (
    normalize_label_string,
    clean_csv_chunk,
    FlowPreprocessor,
    DROPPED_COLUMNS_RATIONALE,
    LABEL_MAP
)

def test_label_normalization():
    """Verify raw labels map accurately to ThreatLens taxonomy."""
    assert normalize_label_string("BENIGN") == "BENIGN"
    assert normalize_label_string("DoS Hulk") == "DOS"
    assert normalize_label_string("DoS GoldenEye") == "DOS"
    assert normalize_label_string("PortScan") == "PORT_SCAN"
    assert normalize_label_string("DDoS") == "DDOS"
    assert normalize_label_string("FTP-Patator") == "BRUTE_FORCE"
    assert normalize_label_string("SSH-Patator") == "BRUTE_FORCE"
    assert normalize_label_string("Bot") == "BOTNET"
    assert normalize_label_string("Web Attack \x96 Brute Force") == "WEB_ATTACK"
    assert normalize_label_string("Web Attack ? XSS") == "WEB_ATTACK"
    assert normalize_label_string("Infiltration") == "OTHER_ATTACK"
    assert normalize_label_string("Heartbleed") == "OTHER_ATTACK"

def test_dropped_columns_rationale():
    """Verify all dropped columns have documented rationale."""
    assert "Fwd Header Length.1" in DROPPED_COLUMNS_RATIONALE
    assert "Bwd PSH Flags" in DROPPED_COLUMNS_RATIONALE
    assert len(DROPPED_COLUMNS_RATIONALE) == 9

def test_clean_csv_chunk_removes_invalids():
    """Verify clean_csv_chunk handles headers, inf values, and dropped columns."""
    sample_df = pd.DataFrame({
        " Destination Port": [80, 443],
        " Flow Duration": [1000, 0],
        "Flow Bytes/s": [150.0, np.inf],
        "Flow Packets/s": [-np.inf, 25.0],
        "Bwd PSH Flags": [0, 0],            # Constant column to drop
        "Fwd Header Length.1": [20, 20],     # Duplicate column to drop
        " Label": ["BENIGN", "DoS Hulk"]
    })
    
    features, labels = clean_csv_chunk(sample_df)
    
    assert "Bwd PSH Flags" not in features.columns
    assert "Fwd Header Length.1" not in features.columns
    assert "Label" not in features.columns
    assert labels.tolist() == ["BENIGN", "DOS"]
    assert not np.isinf(features["Flow Bytes/s"]).any()
    assert not np.isinf(features["Flow Packets/s"]).any()
    assert features["Flow Bytes/s"].isna().sum() == 1  # Replaced inf with NaN

def test_flow_preprocessor_imputation_and_persistence():
    """Verify FlowPreprocessor fits, imputes NaNs/Infs, and persists correctly."""
    train_df = pd.DataFrame({
        "Destination Port": [80, 443, 8080],
        "Flow Duration": [1000.0, 5000.0, 2000.0],
        "Flow Bytes/s": [100.0, np.nan, 300.0],
        "Label": ["BENIGN", "BENIGN", "DOS"]
    })
    
    preprocessor = FlowPreprocessor()
    preprocessor.fit(train_df)
    
    assert preprocessor.fitted is True
    assert "Destination Port" in preprocessor.feature_columns
    assert "Flow Bytes/s" in preprocessor.feature_columns
    assert preprocessor.impute_values["Flow Bytes/s"] == 200.0  # Median of [100, 300]
    
    # Test on unseen evaluation batch with NaNs and Infs
    eval_df = pd.DataFrame({
        "Destination Port": [80, 22],
        "Flow Duration": [1500.0, 0.0],
        "Flow Bytes/s": [np.nan, np.inf]
    })
    
    transformed = preprocessor.transform(eval_df)
    
    # Verify zero NaNs and zero Infs remain
    assert transformed.isna().sum().sum() == 0
    assert not np.isinf(transformed.values).any()
    assert transformed["Flow Bytes/s"].iloc[0] == 200.0
    assert transformed["Flow Bytes/s"].iloc[1] == 200.0
    
    # Verify persistence
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "preprocessor.joblib"
        preprocessor.save(model_path)
        loaded_prep = FlowPreprocessor.load(model_path)
        
        loaded_transformed = loaded_prep.transform(eval_df)
        pd.testing.assert_frame_equal(transformed, loaded_transformed)

def test_processed_partitions_integrity():
    """Verify generated processed parquet files have zero NaNs, zero Infs, and zero duplicate crossover."""
    from threatlens.config import settings
    from threatlens.data.leakage import verify_no_cross_split_contamination
    
    train_path = settings.PROCESSED_DATA_DIR / "clf_train.parquet"
    val_path = settings.PROCESSED_DATA_DIR / "clf_val.parquet"
    test_path = settings.PROCESSED_DATA_DIR / "clf_test.parquet"
    
    assert train_path.exists(), "clf_train.parquet missing"
    assert val_path.exists(), "clf_val.parquet missing"
    assert test_path.exists(), "clf_test.parquet missing"
    
    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)
    
    feat_cols = [c for c in train_df.columns if c != "Label"]
    assert len(feat_cols) == 69
    
    # Verify zero NaNs in any feature column
    assert train_df[feat_cols].isna().sum().sum() == 0
    assert val_df[feat_cols].isna().sum().sum() == 0
    assert test_df[feat_cols].isna().sum().sum() == 0
    
    # Verify zero Infs
    assert not np.isinf(train_df[feat_cols].values).any()
    assert not np.isinf(val_df[feat_cols].values).any()
    assert not np.isinf(test_df[feat_cols].values).any()
    
    # Verify zero cross-split duplicate contamination
    clean_val, overlap_val = verify_no_cross_split_contamination(train_df, val_df, feat_cols)
    assert clean_val is True, f"Found {overlap_val} overlapping records between train and val"
    
    clean_test, overlap_test = verify_no_cross_split_contamination(train_df, test_df, feat_cols)
    assert clean_test is True, f"Found {overlap_test} overlapping records between train and test"
    
    # Verify forecasting windows
    fc_train_path = settings.PROCESSED_DATA_DIR / "forecast_train.parquet"
    fc_val_path = settings.PROCESSED_DATA_DIR / "forecast_val.parquet"
    fc_test_path = settings.PROCESSED_DATA_DIR / "forecast_test.parquet"
    
    assert fc_train_path.exists()
    assert fc_val_path.exists()
    assert fc_test_path.exists()
    
    fc_train = pd.read_parquet(fc_train_path)
    fc_test = pd.read_parquet(fc_test_path)
    
    assert len(fc_train) > 0
    assert len(fc_test) > 0
    # Rolling features must not have NaNs or Infs
    for col in ["rolling_mean_flow_count_3", "rolling_mean_byte_rate_3", "flow_growth_rate"]:
        assert fc_train[col].isna().sum() == 0
        assert not np.isinf(fc_train[col].values).any()

