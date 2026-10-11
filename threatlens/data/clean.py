"""
ThreatLens AI - Data Cleaning and Preprocessing Pipeline
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
import joblib

from threatlens.config import settings

# Canonical label mapping from raw CIC-IDS2017 text to ThreatLens taxonomy
LABEL_MAP = {
    "BENIGN": "BENIGN",
    "DOS HULK": "DOS",
    "DOS GOLDENEYE": "DOS",
    "DOS SLOWLORIS": "DOS",
    "DOS SLOWHTTPTEST": "DOS",
    "PORTSCAN": "PORT_SCAN",
    "DDOS": "DDOS",
    "FTP-PATATOR": "BRUTE_FORCE",
    "SSH-PATATOR": "BRUTE_FORCE",
    "BOT": "BOTNET",
    "INFILTRATION": "OTHER_ATTACK",
    "HEARTBLEED": "OTHER_ATTACK",
}

# Documented rationale for all dropped columns
DROPPED_COLUMNS_RATIONALE = {
    "Fwd Header Length.1": "Exact duplicate column of Fwd Header Length in CIC-IDS2017 export.",
    "Bwd PSH Flags": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Bwd URG Flags": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Fwd Avg Bytes/Bulk": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Fwd Avg Packets/Bulk": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Fwd Avg Bulk Rate": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Bwd Avg Bytes/Bulk": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Bwd Avg Packets/Bulk": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
    "Bwd Avg Bulk Rate": "Zero variance / constant 0 across entire dataset; provides zero discriminative signal.",
}

def normalize_label_string(raw_label: str) -> str:
    """Normalize label string, handling non-ascii encoding quirks in Web Attack names."""
    if not isinstance(raw_label, str):
        raw_label = str(raw_label)
    lbl = raw_label.strip()
    lbl_upper = lbl.upper()
    
    # Check Web Attack patterns specifically
    if "WEB ATTACK" in lbl_upper:
        return "WEB_ATTACK"
        
    for k, v in LABEL_MAP.items():
        if k in lbl_upper:
            return v
            
    return "OTHER_ATTACK"

class FlowPreprocessor:
    """
    Production-ready flow feature preprocessor.
    Fitted strictly on training data; persisted as a versioned joblib artifact.
    """
    def __init__(self):
        self.feature_columns: List[str] = []
        self.impute_values: Dict[str, float] = {}
        self.fitted: bool = False
        self.dropped_columns: List[str] = list(DROPPED_COLUMNS_RATIONALE.keys())

    def fit(self, df: pd.DataFrame):
        """Learn column list and median imputation values strictly from training partition."""
        clean_df = df.copy()
        clean_df.columns = [c.strip() for c in clean_df.columns]
        
        # Remove target column and dropped columns
        cols_to_drop = [c for c in self.dropped_columns if c in clean_df.columns]
        if "Label" in clean_df.columns:
            cols_to_drop.append("Label")
            
        feat_df = clean_df.drop(columns=cols_to_drop, errors="ignore")
        
        # Store exact feature columns in deterministic order
        self.feature_columns = sorted(list(feat_df.columns))
        
        # Compute finite medians for all numeric features
        self.impute_values = {}
        for col in self.feature_columns:
            series = pd.to_numeric(feat_df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            median_val = float(series.median(skipna=True))
            if np.isnan(median_val):
                median_val = 0.0
            self.impute_values[col] = median_val
            
        self.fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply learned imputation and schema ordering to input dataframe."""
        if not self.fitted:
            raise ValueError("FlowPreprocessor must be fitted before calling transform().")
            
        clean_df = df.copy()
        clean_df.columns = [c.strip() for c in clean_df.columns]
        
        # Ensure all required features are present
        for col in self.feature_columns:
            if col not in clean_df.columns:
                clean_df[col] = self.impute_values.get(col, 0.0)
                
        # Select and order columns strictly
        out_df = clean_df[self.feature_columns].copy()
        
        # Convert to numeric, replace inf with nan, impute with learned medians
        for col in self.feature_columns:
            num_series = pd.to_numeric(out_df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            num_series = num_series.fillna(self.impute_values[col])
            out_df[col] = num_series.astype(np.float32)
            
        return out_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def save(self, filepath: Path):
        """Save preprocessor to disk."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: Path) -> "FlowPreprocessor":
        """Load preprocessor from disk."""
        return joblib.load(filepath)

def clean_csv_chunk(chunk: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Clean a raw CSV chunk: trim headers, drop unusable columns, map labels, replace inf."""
    chunk.columns = [c.strip() for c in chunk.columns]
    
    # Extract and normalize labels
    if "Label" in chunk.columns:
        labels = chunk["Label"].apply(normalize_label_string)
    else:
        labels = pd.Series(["BENIGN"] * len(chunk), index=chunk.index)
        
    # Drop known invalid columns
    cols_to_drop = [c for c in DROPPED_COLUMNS_RATIONALE.keys() if c in chunk.columns]
    if "Label" in chunk.columns:
        cols_to_drop.append("Label")
        
    features = chunk.drop(columns=cols_to_drop, errors="ignore")
    
    # Convert all to float32, replace infs with nan
    for col in features.columns:
        features[col] = pd.to_numeric(features[col], errors="coerce").replace([np.inf, -np.inf], np.nan).astype(np.float32)
        
    return features, labels
