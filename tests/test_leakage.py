"""
Unit Tests for ThreatLens Data Leakage Prevention & Duplicate Quarantine
"""

import pytest
import numpy as np
import pandas as pd
from threatlens.data.leakage import (
    compute_row_hashes,
    quarantine_duplicates_across_splits,
    verify_no_cross_split_contamination
)
from threatlens.data.timeline import aggregate_time_windows

def test_duplicate_quarantine_across_splits():
    """Verify duplicate feature vectors are removed from evaluation splits."""
    feature_cols = ["feat_a", "feat_b"]
    
    train_df = pd.DataFrame({
        "feat_a": [1.0, 2.0, 3.0],
        "feat_b": [10.0, 20.0, 30.0],
        "Label": ["BENIGN", "DOS", "BENIGN"]
    })
    
    val_df = pd.DataFrame({
        "feat_a": [1.0, 4.0],  # row 0 is identical to train row 0!
        "feat_b": [10.0, 40.0],
        "Label": ["BENIGN", "PORT_SCAN"]
    })
    
    test_df = pd.DataFrame({
        "feat_a": [2.0, 5.0],  # row 0 is identical to train row 1!
        "feat_b": [20.0, 50.0],
        "Label": ["DOS", "DDOS"]
    })
    
    clean_train, clean_val, clean_test, audit = quarantine_duplicates_across_splits(
        train_df, val_df, test_df, feature_cols
    )
    
    # Val should lose row 0, Test should lose row 0
    assert audit["val_quarantined_duplicates"] == 1
    assert audit["test_quarantined_duplicates"] == 1
    assert len(clean_val) == 1
    assert len(clean_test) == 1
    assert clean_val["feat_a"].iloc[0] == 4.0
    assert clean_test["feat_a"].iloc[0] == 5.0
    
    # Verify zero cross-split contamination
    is_clean, overlap = verify_no_cross_split_contamination(clean_train, clean_val, feature_cols)
    assert is_clean is True
    assert overlap == 0
    
    is_clean, overlap = verify_no_cross_split_contamination(clean_train, clean_test, feature_cols)
    assert is_clean is True
    assert overlap == 0

def test_backward_only_rolling_features_independence():
    """Verify that altering future windows does NOT change past window features."""
    # Create synthetic flows spanning 5 windows (300 seconds)
    rows = []
    for i in range(30):
        rows.append({
            "rel_start_sec": i * 10.0,
            "rel_end_sec": (i * 10.0) + 2.0,
            "Total Length of Fwd Packets": 500,
            "Total Length of Bwd Packets": 500,
            "Total Fwd Packets": 5,
            "Total Backward Packets": 5,
            "SYN Flag Count": 1,
            "ACK Flag Count": 1,
            "FIN Flag Count": 0,
            "RST Flag Count": 0,
            "Flow Duration": 2000000,
            "Label": "BENIGN"
        })
    df_base = pd.DataFrame(rows)
    
    win_base = aggregate_time_windows(df_base, window_size_sec=60, horizon_sec=60)
    base_feat_w0 = win_base.loc[win_base["window_id"] == 0, "rolling_mean_byte_rate_3"].values[0]
    base_feat_w1 = win_base.loc[win_base["window_id"] == 1, "rolling_mean_byte_rate_3"].values[0]
    
    # Now simulate a massive attack in future window 4 (sec 240-300)
    df_attack = df_base.copy()
    attack_rows = []
    for j in range(50):
        attack_rows.append({
            "rel_start_sec": 250.0 + j,
            "rel_end_sec": 251.0 + j,
            "Total Length of Fwd Packets": 50000,
            "Total Length of Bwd Packets": 50000,
            "Total Fwd Packets": 100,
            "Total Backward Packets": 100,
            "SYN Flag Count": 100,
            "ACK Flag Count": 100,
            "FIN Flag Count": 0,
            "RST Flag Count": 0,
            "Flow Duration": 1000000,
            "Label": "DDOS"
        })
    df_attack = pd.concat([df_attack, pd.DataFrame(attack_rows)], ignore_index=True)
    
    win_attack = aggregate_time_windows(df_attack, window_size_sec=60, horizon_sec=60)
    attack_feat_w0 = win_attack.loc[win_attack["window_id"] == 0, "rolling_mean_byte_rate_3"].values[0]
    attack_feat_w1 = win_attack.loc[win_attack["window_id"] == 1, "rolling_mean_byte_rate_3"].values[0]
    
    # Features in early windows 0 and 1 MUST BE EXACTLY IDENTICAL
    assert base_feat_w0 == attack_feat_w0
    assert base_feat_w1 == attack_feat_w1
