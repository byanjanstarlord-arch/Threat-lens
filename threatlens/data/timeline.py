"""
ThreatLens AI - Reconstructed Relative Session Timeline & Backward Window Aggregator

Methodology Documentation:
Because the raw CIC-IDS2017 MachineLearningCSV export omits the original raw pcap packet
timestamps, ThreatLens reconstructs a monotonic relative timeline called:
"Reconstructed Relative Session Timeline".

The timeline is constructed monotonically from cumulative flow arrival intervals and Flow Duration
(in microseconds converted to seconds). Each flow receives:
- rel_start_sec: relative arrival time within the session
- rel_end_sec: rel_start_sec + (Flow Duration / 1e6)

Window Aggregation & Target Formulation:
- Features at window T aggregate ONLY flows completing at or before T (rel_end_sec <= T).
- Rolling features (rolling mean, rolling max, growth rates) look backward across [T-2, T-1, T].
- Future Target Y_T = 1 if any flow with label != 'BENIGN' starts within (T, T + 300s] (5 min horizon).
- Advance Lead Time = attack_onset_rel_sec - T.
Zero future information is permitted to enter the feature vector for window T.
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any
from threatlens.config import settings

def construct_relative_session_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct Reconstructed Relative Session Timeline.
    Uses sequential flow inter-arrival estimates and Flow Duration (microseconds).
    """
    out = df.copy()
    
    # Extract Flow Duration in seconds (CIC-IDS2017 Flow Duration is in microseconds)
    duration_col = [c for c in out.columns if "flow duration" in c.lower()]
    if duration_col:
        flow_dur_sec = (out[duration_col[0]].clip(lower=0) / 1e6).fillna(0.001)
    else:
        flow_dur_sec = pd.Series(0.001, index=out.index)
        
    # Check for Flow IAT Mean (microseconds) to estimate inter-arrival interval
    iat_col = [c for c in out.columns if "flow iat mean" in c.lower()]
    if iat_col:
        iat_sec = (out[iat_col[0]].clip(lower=0) / 1e6).fillna(0.0005)
    else:
        iat_sec = pd.Series(0.0005, index=out.index)
        
    # Relative inter-arrival delta: paced monotonically so flows spread realistically
    delta_starts = (iat_sec * 0.1).clip(lower=0.0001, upper=0.5)
    rel_starts = delta_starts.cumsum() - delta_starts.iloc[0]
    
    out["rel_start_sec"] = rel_starts.astype(np.float64)
    out["rel_end_sec"] = (out["rel_start_sec"] + flow_dur_sec).astype(np.float64)
    return out

def aggregate_time_windows(
    df_with_timeline: pd.DataFrame,
    window_size_sec: int = 60,
    horizon_sec: int = 300
) -> pd.DataFrame:
    """
    Vectorized high-performance window aggregation:
    1. Backward-only features from [t_k, t_k + window_size_sec]
    2. Backward-only rolling features from [t_{k-2}, t_k + window_size_sec]
    3. Future target Y_k from (t_k + window_size_sec, t_k + window_size_sec + horizon_sec]
    """
    df = df_with_timeline.sort_values("rel_start_sec").reset_index(drop=True)
    if len(df) == 0:
        return pd.DataFrame()
        
    max_time = df["rel_end_sec"].max()
    horizon_windows = max(1, horizon_sec // window_size_sec)
    
    # Assign window IDs
    df["end_win_id"] = (df["rel_end_sec"] // window_size_sec).astype(np.int64)
    df["start_win_id"] = (df["rel_start_sec"] // window_size_sec).astype(np.int64)
    
    # Determine full continuous window grid
    max_win_id = int(max_time // window_size_sec)
    all_win_ids = np.arange(0, max(1, max_win_id + 1))
    grid_df = pd.DataFrame({"window_id": all_win_ids})
    grid_df["window_start_sec"] = grid_df["window_id"] * window_size_sec
    grid_df["window_end_sec"] = grid_df["window_start_sec"] + window_size_sec
    
    # Identify relevant columns dynamically
    total_bytes_cols = [c for c in df.columns if "total length of fwd" in c.lower() or "total length of bwd" in c.lower()]
    total_pkts_cols = [c for c in df.columns if "total fwd packets" in c.lower() or "total backward packets" in c.lower()]
    syn_col = [c for c in df.columns if "syn flag count" in c.lower()]
    ack_col = [c for c in df.columns if "ack flag count" in c.lower()]
    fin_col = [c for c in df.columns if "fin flag count" in c.lower()]
    rst_col = [c for c in df.columns if "rst flag count" in c.lower()]
    dur_col = [c for c in df.columns if "flow duration" in c.lower()]
    
    df["_bytes"] = df[total_bytes_cols].sum(axis=1) if total_bytes_cols else 0.0
    df["_pkts"] = df[total_pkts_cols].sum(axis=1) if total_pkts_cols else 0.0
    df["_syn"] = df[syn_col[0]] if syn_col else 0.0
    df["_ack"] = df[ack_col[0]] if ack_col else 0.0
    df["_fin"] = df[fin_col[0]] if fin_col else 0.0
    df["_rst"] = df[rst_col[0]] if rst_col else 0.0
    df["_dur"] = df[dur_col[0]] if dur_col else 0.0
    
    # Aggregate backward features by end_win_id
    win_agg = df.groupby("end_win_id").agg(
        flow_count=("rel_end_sec", "count"),
        total_bytes=("_bytes", "sum"),
        total_packets=("_pkts", "sum"),
        syn_flag_count=("_syn", "sum"),
        ack_flag_count=("_ack", "sum"),
        fin_flag_count=("_fin", "sum"),
        rst_flag_count=("_rst", "sum"),
        mean_flow_duration=("_dur", "mean")
    ).reset_index().rename(columns={"end_win_id": "window_id"})
    
    win_df = pd.merge(grid_df, win_agg, on="window_id", how="left").fillna({
        "flow_count": 0,
        "total_bytes": 0.0,
        "total_packets": 0.0,
        "syn_flag_count": 0.0,
        "ack_flag_count": 0.0,
        "fin_flag_count": 0.0,
        "rst_flag_count": 0.0,
        "mean_flow_duration": 0.0
    })
    
    win_df["byte_rate"] = win_df["total_bytes"] / window_size_sec
    win_df["packet_rate"] = win_df["total_packets"] / window_size_sec
    
    # Backward-only rolling statistics
    win_df["rolling_mean_flow_count_3"] = win_df["flow_count"].rolling(window=3, min_periods=1).mean()
    win_df["rolling_mean_byte_rate_3"] = win_df["byte_rate"].rolling(window=3, min_periods=1).mean()
    win_df["rolling_max_packet_rate_3"] = win_df["packet_rate"].rolling(window=3, min_periods=1).max()
    win_df["flow_growth_rate"] = win_df["flow_count"].pct_change().fillna(0.0).replace([np.inf, -np.inf], 0.0)
    
    # Future Target: track which start_win_ids have malicious flows
    malicious_flows = df[df["Label"] != "BENIGN"]
    if len(malicious_flows) > 0:
        attack_starts = malicious_flows.groupby("start_win_id").agg(
            attack_cnt=("rel_start_sec", "count"),
            first_attack_start=("rel_start_sec", "min"),
            top_category=("Label", lambda s: s.mode()[0] if len(s) > 0 else "BENIGN")
        ).reset_index().rename(columns={"start_win_id": "window_id"})
    else:
        attack_starts = pd.DataFrame(columns=["window_id", "attack_cnt", "first_attack_start", "top_category"])
        
    win_df = pd.merge(win_df, attack_starts, on="window_id", how="left").fillna({
        "attack_cnt": 0,
        "top_category": "BENIGN"
    })
    
    # Vectorized forward horizon target generation:
    # For window w, horizon covers [w+1, w + horizon_windows]
    # We invert series, compute backward rolling sum of size horizon_windows, then invert back
    rev_attacks = win_df["attack_cnt"].iloc[::-1]
    # rolling sum shifted by 1 so window w does not include its own attack count
    rev_future_sum = rev_attacks.rolling(window=horizon_windows, min_periods=1).sum().shift(1)
    win_df["future_attack"] = (rev_future_sum.iloc[::-1].fillna(0.0) > 0).astype(int)
    
    # Rolling forward earliest attack onset
    # Forward lookahead for lead time
    onset_list = []
    lead_list = []
    cat_list = []
    
    n_wins = len(win_df)
    win_arr = win_df.to_dict("records")
    for i in range(n_wins):
        future_recs = win_arr[i+1 : i+1+horizon_windows]
        mal_recs = [r for r in future_recs if r["attack_cnt"] > 0]
        if mal_recs:
            earliest_onset = min(r["first_attack_start"] for r in mal_recs)
            w_end = win_arr[i]["window_end_sec"]
            onset_list.append(float(earliest_onset))
            lead_list.append(max(0.0, float(earliest_onset - w_end)))
            cat_list.append(mal_recs[0]["top_category"])
        else:
            onset_list.append(np.nan)
            lead_list.append(np.nan)
            cat_list.append("BENIGN")
            
    win_df["attack_onset_sec"] = onset_list
    win_df["lead_time_sec"] = lead_list
    win_df["future_attack_category"] = cat_list
    
    # Drop intermediate columns
    win_df = win_df.drop(columns=["attack_cnt", "first_attack_start", "top_category"], errors="ignore")
    
    # Discard trailing windows where the full horizon cannot be observed
    if len(win_df) > horizon_windows:
        win_df = win_df.iloc[:-horizon_windows].reset_index(drop=True)
        
    return win_df
