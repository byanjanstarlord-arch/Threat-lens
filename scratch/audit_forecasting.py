import joblib, json
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score, confusion_matrix
)
from threatlens.ml.forecaster import engineer_window_features

# 1. Load data
train_df = engineer_window_features(pd.read_parquet('data/processed/forecast_train.parquet'))
val_df = engineer_window_features(pd.read_parquet('data/processed/forecast_val.parquet'))
test_df = engineer_window_features(pd.read_parquet('data/processed/forecast_test.parquet'))

model = joblib.load('models/v1/forecasting/xgboost_forecaster.joblib')
with open('models/v1/forecasting/forecaster_features.json') as f:
    features = json.load(f)

print('=== 1. TEMPORAL CLASS PREVALENCE ===')
p_tr = float(train_df['future_attack'].mean())
p_va = float(val_df['future_attack'].mean())
p_te = float(test_df['future_attack'].mean())
print(f'Train future-attack prevalence: {int(train_df["future_attack"].sum())} / {len(train_df)} ({p_tr*100:.2f}%)')
print(f'Val future-attack prevalence:   {int(val_df["future_attack"].sum())} / {len(val_df)} ({p_va*100:.2f}%)')
print(f'Test future-attack prevalence:  {int(test_df["future_attack"].sum())} / {len(test_df)} ({p_te*100:.2f}%)')
print(f'Trivial Random PR-AUC Baseline (Test Prevalence): {p_te:.4f}')

# 2. Validation Threshold Selection
X_val = val_df[features].values
y_val = val_df['future_attack'].values
probs_val = model.predict_proba(X_val)[:, 1]

best_thresh = 0.50
best_f1_val = 0.0
thresh_results = []
for t in np.arange(0.10, 0.91, 0.01):
    preds = (probs_val >= t).astype(int)
    p = float(precision_score(y_val, preds, zero_division=0))
    r = float(recall_score(y_val, preds, zero_division=0))
    f = float(f1_score(y_val, preds, zero_division=0))
    thresh_results.append((float(t), p, r, f))
    if f > best_f1_val:
        best_f1_val = f
        best_thresh = float(t)

print(f'\n=== 2. VALIDATION THRESHOLD SELECTION ===')
print(f'Optimal Validation Threshold (Max F1): {best_thresh:.2f} (Val F1: {best_f1_val:.4f})')

p_50 = float(precision_score(y_val, (probs_val >= 0.50).astype(int), zero_division=0))
r_50 = float(recall_score(y_val, (probs_val >= 0.50).astype(int), zero_division=0))
f_50 = float(f1_score(y_val, (probs_val >= 0.50).astype(int), zero_division=0))
print(f'Validation at threshold=0.50: Prec={p_50:.4f}, Rec={r_50:.4f}, F1={f_50:.4f}')

# Show table of thresholds around 0.30 - 0.70
print('\nThreshold Scan on Validation Set:')
print(f'{"Threshold":<10} | {"Precision":<10} | {"Recall":<10} | {"F1":<10}')
for t, p, r, f in thresh_results:
    if round(t, 2) in [0.20, 0.30, 0.40, 0.45, 0.48, 0.50, 0.52, 0.55, 0.60, 0.70]:
        print(f'{t:<10.2f} | {p:<10.4f} | {r:<10.4f} | {f:<10.4f}')
