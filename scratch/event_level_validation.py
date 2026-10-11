import sys
sys.path.insert(0, '.')
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix
)
from threatlens.ml.forecaster import engineer_window_features

# 1. Load trained model & test data
model = joblib.load('models/v1/forecasting/xgboost_forecaster.joblib')
with open('models/v1/forecasting/forecaster_features.json') as f:
    features = json.load(f)

test_df = engineer_window_features(pd.read_parquet('data/processed/forecast_test.parquet'))
X_test = test_df[features].values
y_test = test_df['future_attack'].values
probs_test = model.predict_proba(X_test)[:, 1]

# Load Friday malicious flows to get exact ground truth campaigns
df_clean = pd.read_parquet('data/interim/all_flows_clean.parquet')
test_sessions = [s for s in df_clean['session'].unique() if 'friday' in s.lower()]
sub_df = df_clean[df_clean['session'].isin(test_sessions)].copy()

from threatlens.data.timeline import construct_relative_session_timeline
timeline = construct_relative_session_timeline(sub_df)
mal = timeline[timeline['Label'] != 'BENIGN'].sort_values('rel_start_sec').reset_index(drop=True)

# Define campaigns: gap > 300s (5 minutes)
mal['gap'] = mal['rel_start_sec'].diff().fillna(0)
campaign_ids = np.zeros(len(mal), dtype=int)
current_c = 0
for i in range(len(mal)):
    if mal.loc[i, 'gap'] > 300:
        current_c += 1
    campaign_ids[i] = current_c
mal['campaign_id'] = campaign_ids

campaigns = []
for cid, grp in mal.groupby('campaign_id'):
    c_start = float(grp['rel_start_sec'].min())
    c_end = float(grp['rel_end_sec'].max())
    top_cat = grp['Label'].value_counts().index[0]
    win_start = int(c_start // 60)
    win_end = int(c_end // 60)
    campaigns.append({
        'campaign_id': cid,
        'category': top_cat,
        'start_sec': c_start,
        'end_sec': c_end,
        'start_win': win_start,
        'end_win': win_end,
        'flow_count': len(grp),
        'duration_sec': c_end - c_start
    })

print(f'Total Ground-Truth Attack Campaigns: {len(campaigns)}')

# Run evaluation at threshold = 0.50
tau = 0.50
preds_test = (probs_test >= tau).astype(int)

# Window-level metrics
cm = confusion_matrix(y_test, preds_test)
tn, fp, fn, tp = cm.ravel()
prec = precision_score(y_test, preds_test, zero_division=0)
rec = recall_score(y_test, preds_test, zero_division=0)
f1 = f1_score(y_test, preds_test, zero_division=0)
roc_auc = roc_auc_score(y_test, probs_test)
pr_auc = average_precision_score(y_test, probs_test)
prevalence = float(y_test.mean())
fpr = fp / max(1, fp + tn)

print('\n============================================================')
print('WINDOW-LEVEL FORECASTING EVALUATION (Threshold = 0.50)')
print('============================================================')
print(f'Total Windows: {len(test_df)}')
print(f'True Positives (TP):  {tp}')
print(f'False Positives (FP): {fp}')
print(f'True Negatives (TN):  {tn}')
print(f'False Negatives (FN): {fn}')
print(f'Precision:            {prec:.4f} ({prec*100:.2f}%)')
print(f'Recall:               {rec:.4f} ({rec*100:.2f}%)')
print(f'F1-Score:             {f1:.4f}')
print(f'False Positive Rate:  {fpr:.4f} ({fpr*100:.2f}%)')
print(f'ROC-AUC:              {roc_auc:.4f}')
print(f'PR-AUC:               {pr_auc:.4f}')
print(f'Trivial Baseline PR-AUC: {prevalence:.4f} (Excess PR-AUC: +{pr_auc - prevalence:.4f})')

# Now distinguish Onset Warnings vs Ongoing-Campaign Warnings
# For each test window w (start: w*60, end: (w+1)*60):
# If pred == 1 and y == 1 (TP):
# Determine if window w_end <= start_sec of the impending campaign (ONSET WARNING)
# OR if window w is inside [start_sec, end_sec] of an active campaign (ONGOING WARNING)

onset_warnings = []
ongoing_warnings = []

test_df['predicted'] = preds_test
test_df['prob'] = probs_test

for idx, row in test_df.iterrows():
    w_id = int(row['window_id'])
    w_end = float(row['window_end_sec'])
    pred = int(row['predicted'])
    actual = int(row['future_attack'])
    lead = float(row['lead_time_sec']) if not pd.isna(row['lead_time_sec']) else None
    
    if pred == 1 and actual == 1:
        # True Positive warning: find which campaign it warned for
        # It warned for an attack in (w_end, w_end + 300s]
        # Check if w_end is before the campaign start
        # A warning is an ONSET warning if the impending campaign starts in the future (w_end <= c_start)
        # Find campaign whose start is in (w_end, w_end + 300]
        impending_campaign = None
        for c in campaigns:
            if w_end < c['start_sec'] <= w_end + 300.0:
                impending_campaign = c
                break
                
        if impending_campaign is not None:
            # Genuine Onset Warning!
            onset_lead = impending_campaign['start_sec'] - w_end
            onset_warnings.append({
                'window_id': w_id,
                'window_end_sec': w_end,
                'prob': row['prob'],
                'campaign_id': impending_campaign['campaign_id'],
                'campaign_cat': impending_campaign['category'],
                'campaign_start_sec': impending_campaign['start_sec'],
                'onset_lead_sec': onset_lead
            })
        else:
            # The campaign is ALREADY active!
            ongoing_warnings.append({
                'window_id': w_id,
                'window_end_sec': w_end,
                'prob': row['prob'],
                'lead_sec': lead
            })

print('\n============================================================')
print('WARNING CATEGORY BREAKDOWN')
print('============================================================')
print(f'Total Positive Warnings Triggered: {tp + fp} ({tp} TP, {fp} FP)')
print(f'  - Genuine Pre-Onset Warnings:   {len(onset_warnings)} ({len(onset_warnings)/tp*100:.2f}% of TPs)')
print(f'  - Ongoing-Campaign Warnings:   {len(ongoing_warnings)} ({len(ongoing_warnings)/tp*100:.2f}% of TPs)')
print(f'  - False Positive Forecasts:    {fp}')

# -----------------------------------------------------------------------------
# CAMPAIGN-LEVEL / EVENT-LEVEL EVALUATION
# -----------------------------------------------------------------------------
campaign_results = []
for c in campaigns:
    cid = c['campaign_id']
    c_start = c['start_sec']
    # Preceding windows whose horizon covers c_start:
    # (w_end, w_end + 300] covers c_start => c_start - 300 <= w_end < c_start
    pre_onset_wins = test_df[(test_df['window_end_sec'] >= c_start - 300) & (test_df['window_end_sec'] < c_start)]
    
    # Check if any pre-onset window triggered a positive forecast
    pos_pre_wins = pre_onset_wins[pre_onset_wins['predicted'] == 1]
    has_onset_warning = len(pos_pre_wins) > 0
    
    first_warning_lead = None
    first_warning_win = None
    if has_onset_warning:
        # Earliest warning window
        earliest_w = pos_pre_wins.iloc[0]
        first_warning_win = int(earliest_w['window_id'])
        first_warning_lead = float(c_start - earliest_w['window_end_sec'])
        
    campaign_results.append({
        'campaign_id': cid,
        'category': c['category'],
        'start_sec': c_start,
        'start_win': c['start_win'],
        'has_onset_warning': has_onset_warning,
        'first_warning_win': first_warning_win,
        'first_warning_lead_sec': first_warning_lead,
        'flows': c['flow_count']
    })

df_camp = pd.DataFrame(campaign_results)
detected_campaigns = df_camp[df_camp['has_onset_warning'] == True]
onset_leads = detected_campaigns['first_warning_lead_sec'].dropna().values

print('\n============================================================')
print('EVENT-LEVEL / CAMPAIGN-LEVEL EVALUATION (27 CAMPAIGNS)')
print('============================================================')
print(f'Total Attack Campaigns in Test Timeline: {len(campaigns)}')
print(f'Campaigns with Genuine Pre-Onset Warning: {len(detected_campaigns)} / {len(campaigns)} ({len(detected_campaigns)/len(campaigns)*100:.2f}%)')

print('\nCampaign-by-Campaign Onset Warning Results:')
for idx, r in df_camp.iterrows():
    warn_str = f"YES (Lead: {r['first_warning_lead_sec']:>7.2f}s in Win #{r['first_warning_win']:>3})" if r['has_onset_warning'] else "NO  (Missed onset)"
    print(f"  Campaign #{r['campaign_id']:>2} [{r['category']:<10}]: Onset @ {r['start_sec']:>9.2f}s (Win #{r['start_win']:>3}) -> Pre-Warning: {warn_str}")

print('\n============================================================')
print('GENUINE ONSET LEAD-TIME DISTRIBUTION (EVENT-LEVEL)')
print('============================================================')
if len(onset_leads) > 0:
    print(f'Number of Campaigns with Onset Warnings: {len(onset_leads)}')
    print(f'Mean Onset Lead Time:   {np.mean(onset_leads):.3f} seconds')
    print(f'Median Onset Lead Time: {np.median(onset_leads):.3f} seconds')
    print(f'P25 Onset Lead Time:    {np.percentile(onset_leads, 25):.3f} seconds')
    print(f'P75 Onset Lead Time:    {np.percentile(onset_leads, 75):.3f} seconds')
    print(f'P90 Onset Lead Time:    {np.percentile(onset_leads, 90):.3f} seconds')
    print(f'P95 Onset Lead Time:    {np.percentile(onset_leads, 95):.3f} seconds')
    print(f'Max Onset Lead Time:    {np.max(onset_leads):.3f} seconds')
    
    print('\nOnset Lead Time Thresholds:')
    print(f'  > 5 sec:   {np.mean(onset_leads > 5)*100:.2f}% ({np.sum(onset_leads > 5)} / {len(onset_leads)})')
    print(f'  > 10 sec:  {np.mean(onset_leads > 10)*100:.2f}% ({np.sum(onset_leads > 10)} / {len(onset_leads)})')
    print(f'  > 30 sec:  {np.mean(onset_leads > 30)*100:.2f}% ({np.sum(onset_leads > 30)} / {len(onset_leads)})')
    print(f'  > 60 sec:  {np.mean(onset_leads > 60)*100:.2f}% ({np.sum(onset_leads > 60)} / {len(onset_leads)})')
    print(f'  > 120 sec: {np.mean(onset_leads > 120)*100:.2f}% ({np.sum(onset_leads > 120)} / {len(onset_leads)})')
