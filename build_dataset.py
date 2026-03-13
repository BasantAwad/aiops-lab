import json
import pandas as pd
import json

# ============================================================================
# [LAB WORK 3] - ML Anomaly Detection
# This script is part of Lab 3. It parses the raw Telemetry JSON logs into
# a Pandas DataFrame, groups them into 30-second sliding windows, and
# engineers 11 ML features (latency stats, error rates, endpoint frequencies).
# ============================================================================

import numpy as np
from datetime import datetime

print("Loading logs.json...")
try:
    with open('logs.json', 'r') as f:
        # File contains multiple concatenated JSON lines or objects
        content = f.read().strip()
        # Handle cases where the logger just appends JSON objects continuously (e.g. `}{`)
        content = content.replace('}\n{', '},{')
        if not content.startswith('['):
            content = '[' + content + ']'
        logs = json.loads(content)
except Exception as e:
    print(f"Failed to parse logs: {e}")
    exit(1)

print(f"Loaded {len(logs)} log entries.")

df = pd.DataFrame(logs)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp').sort_index()

# 1. We need to group into 30-second windows.
window = '30s'

print("Engineering features over 30s windows...")

# We calculate features across ALL endpoints combined to find system-level anomalies
features = []

for t_start, window_df in df.groupby(pd.Grouper(freq=window)):
    if len(window_df) == 0:
        continue
        
    avg_latency = window_df['latency_ms'].mean()
    max_latency = window_df['latency_ms'].max()
    latency_std = window_df['latency_ms'].std()
    if pd.isna(latency_std):
        latency_std = 0.0
        
    request_rate = len(window_df) / 30.0  # requests per second in this window
    
    error_count = len(window_df[window_df['status_code'] >= 400])
    error_rate = error_count / len(window_df) if len(window_df) > 0 else 0
    errors_per_window = error_count
    
    # Endpoint frequencies
    endpoints = window_df['path'].value_counts()
    freq_normal = endpoints.get('/api/normal', 0) / len(window_df)
    freq_slow = endpoints.get('/api/slow', 0) / len(window_df)
    freq_db = endpoints.get('/api/db', 0) / len(window_df)
    freq_error = endpoints.get('/api/error', 0) / len(window_df)
    freq_validate = endpoints.get('/api/validate', 0) / len(window_df)
    
    # Ground truth labels
    # We load ground_truth.json to label anomalous windows
    is_anomaly = 0
    
    features.append({
        'timestamp': t_start,
        'avg_latency': avg_latency,
        'max_latency': max_latency,
        'latency_std': latency_std,
        'request_rate': request_rate,
        'error_rate': error_rate,
        'errors_per_window': errors_per_window,
        'freq_normal': freq_normal,
        'freq_slow': freq_slow,
        'freq_db': freq_db,
        'freq_error': freq_error,
        'freq_validate': freq_validate,
        'is_anomaly': is_anomaly # placeholder, will update below
    })

dataset_df = pd.DataFrame(features)

# Apply ground truth labels
print("Applying ground truth labels...")
try:
    with open('ground_truth.json', 'r') as f:
        gt = json.load(f)
        anomaly_start = pd.to_datetime(gt['anomaly_start_iso'])
        anomaly_end = pd.to_datetime(gt['anomaly_end_iso'])
        
        # A window is anomalous if it overlaps the start/end bounds.
        # Window is [t, t + 30s]. Overlaps if: t < anomaly_end AND t + 30s > anomaly_start
        dataset_df['is_anomaly'] = dataset_df['timestamp'].apply(
            lambda t: 1 if (t <= anomaly_end) and (t + pd.Timedelta(seconds=30) >= anomaly_start) else 0
        )
except Exception as e:
    print(f"Warning: Could not apply ground truth: {e}")

# Save the dataset
output_file = 'aiops_dataset.csv'
dataset_df.to_csv(output_file, index=False)
print(f"Dataset generated with {len(dataset_df)} windows and saved to {output_file}.")
