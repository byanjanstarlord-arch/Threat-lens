import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

# Load clean parquet to see Friday flows
df = pd.read_parquet('data/interim/all_flows_clean.parquet')
test_sessions = [s for s in df['session'].unique() if 'friday' in s.lower()]
print('Test sessions (Friday):', test_sessions)

sub_df = df[df['session'].isin(test_sessions)].copy()
from threatlens.data.timeline import construct_relative_session_timeline
timeline = construct_relative_session_timeline(sub_df)

mal = timeline[timeline['Label'] != 'BENIGN'].sort_values('rel_start_sec').reset_index(drop=True)
print(f'Total malicious flows in Friday test partition: {len(mal)}')
print('Malicious flow label distribution:')
print(mal['Label'].value_counts())

earliest = float(mal['rel_start_sec'].min())
latest = float(mal['rel_start_sec'].max())
print(f'Earliest attack start time: {earliest:.3f}s (Window #{int(earliest // 60)})')
print(f'Latest attack start time:   {latest:.3f}s (Window #{int(latest // 60)})')

# Cluster malicious flows into attack campaigns based on inter-arrival gaps
# If gap between consecutive attack flows > 300s (5 minutes), define as new campaign
mal['gap'] = mal['rel_start_sec'].diff().fillna(0)
campaign_breaks = mal[mal['gap'] > 300].index.tolist()
print(f'\nDetected campaign boundaries (gaps > 300s): {len(campaign_breaks)} breaks -> {len(campaign_breaks)+1} campaigns')

campaign_ids = np.zeros(len(mal), dtype=int)
current_c = 0
for i in range(len(mal)):
    if mal.loc[i, 'gap'] > 300:
        current_c += 1
    campaign_ids[i] = current_c

mal['campaign_id'] = campaign_ids

print('\nCampaign Details:')
for cid, grp in mal.groupby('campaign_id'):
    c_start = grp['rel_start_sec'].min()
    c_end = grp['rel_end_sec'].max()
    top_cat = grp['Label'].value_counts().index[0]
    win_start = int(c_start // 60)
    win_end = int(c_end // 60)
    print(f'Campaign #{cid}: Category={top_cat:<12} | Flows={len(grp):>6} | Start={c_start:>9.2f}s (Win #{win_start:>3}) | End={c_end:>9.2f}s (Win #{win_end:>3}) | Duration={(c_end - c_start):>8.2f}s')
