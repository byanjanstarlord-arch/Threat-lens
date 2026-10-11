import sys
sys.path.insert(0, '.')
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix
)
from threatlens.ml.forecaster import engineer_window_features

# 1. Load model and test windows
model = joblib.load('models/v1/forecasting/xgboost_forecaster.joblib')
with open('models/v1/forecasting/forecaster_features.json') as f:
    features = json.load(f)

test_df = engineer_window_features(pd.read_parquet('data/processed/forecast_test.parquet'))
X_test = test_df[features].values
y_test = test_df['future_attack'].values
probs_test = model.predict_proba(X_test)[:, 1]
preds_test = (probs_test >= 0.50).astype(int)

test_df['pred'] = preds_test
test_df['prob'] = probs_test

# 2. Load Friday flows from interim clean parquet
df_clean = pd.read_parquet('data/interim/all_flows_clean.parquet')
test_sessions = [s for s in df_clean['session'].unique() if 'friday' in s.lower()]
sub_df = df_clean[df_clean['session'].isin(test_sessions)].copy()

from threatlens.data.timeline import construct_relative_session_timeline
timeline = construct_relative_session_timeline(sub_df)
mal = timeline[timeline['Label'] != 'BENIGN'].sort_values('rel_start_sec').reset_index(drop=True)

# -----------------------------------------------------------------------------
# TASK 1: Generate Campaign Manifest (gap > 300s)
# -----------------------------------------------------------------------------
mal['gap'] = mal['rel_start_sec'].diff().fillna(0)
campaign_ids_300 = np.zeros(len(mal), dtype=int)
current_c = 0
for i in range(len(mal)):
    if mal.loc[i, 'gap'] > 300:
        current_c += 1
    campaign_ids_300[i] = current_c
mal['campaign_id_300'] = campaign_ids_300

campaign_manifest = []
total_300_campaigns = current_c + 1
assert total_300_campaigns == 27, f"Expected 27 campaigns, got {total_300_campaigns}"

for cid, grp in mal.groupby('campaign_id_300'):
    c_start = float(grp['rel_start_sec'].min())
    c_end = float(grp['rel_end_sec'].max())
    top_cat = str(grp['Label'].value_counts().index[0])
    win_start = int(c_start // 60)
    win_end = int(c_end // 60)
    flow_cnt = int(len(grp))
    dur = float(c_end - c_start)
    
    # Preceding windows whose 5-min horizon (w_end, w_end + 300] covers c_start
    pre_onset_wins = test_df[(test_df['window_end_sec'] >= c_start - 300) & (test_df['window_end_sec'] < c_start)]
    pos_pre_wins = pre_onset_wins[pre_onset_wins['pred'] == 1]
    
    # Active campaign windows
    active_wins = test_df[(test_df['window_start_sec'] <= c_end) & (test_df['window_end_sec'] >= c_start)]
    pos_active_wins = active_wins[active_wins['pred'] == 1]
    
    warned_before_onset = len(pos_pre_wins) > 0
    warned_only_after_onset = (not warned_before_onset) and (len(pos_active_wins) > 0)
    
    first_warning_ts = None
    first_warning_lead = None
    first_warning_win = None
    
    if warned_before_onset:
        earliest_w = pos_pre_wins.iloc[0]
        first_warning_win = int(earliest_w['window_id'])
        first_warning_ts = float(earliest_w['window_end_sec'])
        first_warning_lead = float(c_start - first_warning_ts)
    elif warned_only_after_onset:
        earliest_w = pos_active_wins.iloc[0]
        first_warning_win = int(earliest_w['window_id'])
        first_warning_ts = float(earliest_w['window_end_sec'])
        first_warning_lead = 0.0
        
    campaign_manifest.append({
        'campaign_id': int(cid),
        'attack_type': top_cat,
        'first_malicious_flow_timestamp_sec': c_start,
        'last_malicious_flow_timestamp_sec': c_end,
        'duration_sec': dur,
        'malicious_flow_count': flow_cnt,
        'first_forecast_warning_timestamp_sec': first_warning_ts,
        'first_forecast_warning_window_id': first_warning_win,
        'warning_occurred_before_onset': bool(warned_before_onset),
        'onset_lead_time_sec': first_warning_lead,
        'warning_occurred_only_after_onset': bool(warned_only_after_onset)
    })

manifest_path = Path('reports/forecasting_campaign_manifest.json')
with open(manifest_path, 'w') as f:
    json.dump({
        'total_campaigns': len(campaign_manifest),
        'definition': 'Inter-arrival gap > 300s across malicious flows in Friday test partition',
        'campaigns_with_pre_onset_warning': sum(c['warning_occurred_before_onset'] for c in campaign_manifest),
        'campaign_detection_rate_pct': sum(c['warning_occurred_before_onset'] for c in campaign_manifest) / len(campaign_manifest) * 100,
        'campaigns': campaign_manifest
    }, f, indent=2)

print(f"Saved manifest to {manifest_path}. Total campaigns: {len(campaign_manifest)}")

# -----------------------------------------------------------------------------
# TASK 2: Campaign Definition Sensitivity Analysis (60s, 120s, 300s, 600s)
# -----------------------------------------------------------------------------
sensitivity_results = []
for gap_thresh in [60, 120, 300, 600]:
    camp_ids = np.zeros(len(mal), dtype=int)
    c_idx = 0
    for i in range(len(mal)):
        if mal.loc[i, 'gap'] > gap_thresh:
            c_idx += 1
        camp_ids[i] = c_idx
    mal['temp_camp_id'] = camp_ids
    
    num_camps = c_idx + 1
    leads = []
    detected_cnt = 0
    
    for cid, grp in mal.groupby('temp_camp_id'):
        c_start = float(grp['rel_start_sec'].min())
        pre_wins = test_df[(test_df['window_end_sec'] >= c_start - 300) & (test_df['window_end_sec'] < c_start)]
        pos_pre = pre_wins[pre_wins['pred'] == 1]
        if len(pos_pre) > 0:
            detected_cnt += 1
            earliest_w = pos_pre.iloc[0]
            leads.append(float(c_start - earliest_w['window_end_sec']))
            
    pct_detected = (detected_cnt / num_camps) * 100
    mean_lead = float(np.mean(leads)) if leads else 0.0
    median_lead = float(np.median(leads)) if leads else 0.0
    
    sensitivity_results.append({
        'gap_threshold_sec': gap_thresh,
        'number_of_campaigns': num_camps,
        'campaigns_with_pre_onset_warning': detected_cnt,
        'campaign_detection_rate_pct': pct_detected,
        'mean_onset_lead_sec': mean_lead,
        'median_onset_lead_sec': median_lead
    })

print("\n=== SENSITIVITY ANALYSIS ===")
for s in sensitivity_results:
    is_prim = " [PRIMARY]" if s['gap_threshold_sec'] == 300 else ""
    print(f"Gap: {s['gap_threshold_sec']:>3}s{is_prim:<10} | Campaigns: {s['number_of_campaigns']:>2} | Detected: {s['campaigns_with_pre_onset_warning']:>2} ({s['campaign_detection_rate_pct']:>5.2f}%) | Mean Lead: {s['mean_onset_lead_sec']:>6.2f}s | Median Lead: {s['median_onset_lead_sec']:>6.2f}s")

# -----------------------------------------------------------------------------
# TASK 3: Simple Forecasting Baselines
# -----------------------------------------------------------------------------
# Ground truth future attack in test: y_test
# All baselines evaluated strictly on Friday test partition (743 windows)

# Baseline A: Majority-class predictor
# In train set, future_attack=1 is 66.01% (majority). A majority classifier predicts 1 for all windows.
pred_base_a = np.ones(len(test_df), dtype=int)
prob_base_a = np.full(len(test_df), 1.0)

# Baseline B: Persistence Predictor
# If current/recent window contains attack activity (byte rate > 200KB/s or packet rate > 300pkts/s or syn flags > 10 in window T), predict attack in next 5 min.
# Strictly leakage-free: uses ONLY window T telemetry!
pred_base_b = ((test_df['packet_rate'] > 100.0) | (test_df['syn_flag_count'] > 5.0) | (test_df['byte_rate'] > 100000.0)).astype(int).values
prob_base_b = test_df['packet_rate'].clip(0, 1000).values / 1000.0

# Baseline C: Traffic Intensity / Flow Count threshold predictor
# High flow count in window T (flow_count > 100 flows in past 60s)
pred_base_c = (test_df['flow_count'] > 100).astype(int).values
prob_base_c = (test_df['flow_count'].clip(0, 500).values / 500.0)

def evaluate_baseline(name, preds, probs):
    cm = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()
    p = precision_score(y_test, preds, zero_division=0)
    r = recall_score(y_test, preds, zero_division=0)
    f = f1_score(y_test, preds, zero_division=0)
    roc = roc_auc_score(y_test, probs) if len(np.unique(probs)) > 1 else 0.50
    pr = average_precision_score(y_test, probs) if len(np.unique(probs)) > 1 else y_test.mean()
    
    # Event-level detection on the 27 campaigns
    test_df['temp_pred'] = preds
    onset_cnt = 0
    for c in campaign_manifest:
        c_start = c['first_malicious_flow_timestamp_sec']
        pre_wins = test_df[(test_df['window_end_sec'] >= c_start - 300) & (test_df['window_end_sec'] < c_start)]
        if len(pre_wins[pre_wins['temp_pred'] == 1]) > 0:
            onset_cnt += 1
            
    # Number of genuine pre-onset window predictions
    # (predicted == 1 on windows that are before some campaign start)
    onset_warn_wins = 0
    for idx, row in test_df[test_df['temp_pred'] == 1].iterrows():
        w_end = row['window_end_sec']
        if any(w_end < c['first_malicious_flow_timestamp_sec'] <= w_end + 300 for c in campaign_manifest):
            onset_warn_wins += 1
            
    return {
        'model': name,
        'precision': p,
        'recall': r,
        'f1_score': f,
        'roc_auc': roc,
        'pr_auc': pr,
        'campaign_detection_rate': (onset_cnt / 27) * 100,
        'campaigns_detected': onset_cnt,
        'pre_onset_warning_windows': onset_warn_wins,
        'tp': int(tp),
        'fp': int(fp),
        'tn': int(tn),
        'fn': int(fn)
    }

base_a_res = evaluate_baseline("Baseline A: Majority-Class Predictor (Constant 1)", pred_base_a, prob_base_a)
base_b_res = evaluate_baseline("Baseline B: Persistence / Recent Activity Predictor", pred_base_b, prob_base_b)
base_c_res = evaluate_baseline("Baseline C: Traffic Intensity / Flow Count Predictor", pred_base_c, prob_base_c)
xgb_res = evaluate_baseline("ThreatLens XGBoost Temporal Forecaster", preds_test, probs_test)

print("\n=== BASELINE COMPARISON ===")
for res in [base_a_res, base_b_res, base_c_res, xgb_res]:
    print(f"\nModel: {res['model']}")
    print(f"  Precision: {res['precision']*100:.2f}% | Recall: {res['recall']*100:.2f}% | F1: {res['f1_score']:.4f}")
    print(f"  PR-AUC:    {res['pr_auc']:.4f} | ROC-AUC: {res['roc_auc']:.4f}")
    print(f"  Campaigns Detected (Pre-Onset): {res['campaigns_detected']} / 27 ({res['campaign_detection_rate']:.2f}%)")
    print(f"  Pre-Onset Warning Windows:     {res['pre_onset_warning_windows']}")
    print(f"  Confusion Matrix: TP={res['tp']}, FP={res['fp']}, TN={res['tn']}, FN={res['fn']}")

# Save baselines report
with open('reports/forecasting_baselines_comparison.json', 'w') as f:
    json.dump({
        'test_windows_count': len(test_df),
        'trivial_baseline_pr_auc': float(y_test.mean()),
        'sensitivity_analysis': sensitivity_results,
        'baselines': [base_a_res, base_b_res, base_c_res, xgb_res]
    }, f, indent=2)

print("\nSaved baselines to reports/forecasting_baselines_comparison.json")
