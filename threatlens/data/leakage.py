"""
ThreatLens AI - Leakage Prevention & Duplicate Quarantine Module
"""

import hashlib
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List

def compute_row_hashes(df: pd.DataFrame, feature_cols: List[str]) -> pd.Series:
    """Compute deterministic 64-bit integer hashes for feature rows to track duplicate content."""
    # Round floats to 4 decimals to ensure robust numeric identity comparison
    rounded_df = df[feature_cols].copy()
    for col in rounded_df.select_dtypes(include=[np.number]).columns:
        rounded_df[col] = rounded_df[col].round(4).fillna(-999999.0)
    return pd.util.hash_pandas_object(rounded_df, index=False)

def quarantine_duplicates_across_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Quarantine duplicate records so identical feature vectors never cross evaluation boundaries.
    Any record in val or test that exists in train is quarantined and removed from val/test.
    """
    train_hashes = set(compute_row_hashes(train_df, feature_cols))
    
    val_hashes = compute_row_hashes(val_df, feature_cols)
    val_overlap_mask = val_hashes.isin(train_hashes)
    clean_val = val_df[~val_overlap_mask].copy()
    
    test_hashes = compute_row_hashes(test_df, feature_cols)
    test_overlap_mask = test_hashes.isin(train_hashes)
    clean_test = test_df[~test_overlap_mask].copy()
    
    audit_report = {
        "train_rows": len(train_df),
        "val_initial_rows": len(val_df),
        "val_quarantined_duplicates": int(val_overlap_mask.sum()),
        "val_final_rows": len(clean_val),
        "test_initial_rows": len(test_df),
        "test_quarantined_duplicates": int(test_overlap_mask.sum()),
        "test_final_rows": len(clean_test)
    }
    
    return train_df, clean_val, clean_test, audit_report

def verify_no_cross_split_contamination(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    feature_cols: List[str]
) -> Tuple[bool, int]:
    """Verify zero identical feature records exist across train and eval partitions."""
    train_hashes = set(compute_row_hashes(train_df, feature_cols))
    eval_hashes = set(compute_row_hashes(eval_df, feature_cols))
    intersection = train_hashes.intersection(eval_hashes)
    return len(intersection) == 0, len(intersection)
