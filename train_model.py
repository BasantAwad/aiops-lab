import pandas as pd
import numpy as np
import json

# ============================================================================
# [LAB WORK 3] - ML Anomaly Detection
# This script trains an Isolation Forest unsupervised machine learning model
# exclusively on normal Baseline network behavior. It then predicts anomalies
# on the full dataset and plots latency/error rate timeliness.
# ============================================================================

import numpy as np
import json
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

print("Loading dataset...")
df = pd.read_csv('aiops_dataset.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# We need to strictly train the model *only on normal behavior* 
# to establish a baseline of what healthy API traffic looks like.
# We find the exact anomaly injection window from ground truth.
with open('ground_truth.json', 'r') as f:
    gt = json.load(f)
    anomaly_start = pd.to_datetime(gt['anomaly_start_iso'])
    
# Training set: Only data BEFORE the anomaly started
train_df = df[df['timestamp'] < anomaly_start].copy()

# Features for training
features = [
    'avg_latency', 'max_latency', 'latency_std',
    'request_rate', 'error_rate', 'errors_per_window',
    'freq_normal', 'freq_slow', 'freq_db', 'freq_error', 'freq_validate'
]

X_train = train_df[features]

print(f"Training Isolation Forest on {len(X_train)} normal windows...")
# Contamination is set to 'auto' since theoretical normal data shouldn't have many outliers.
# The Isolation Forest algorithm isolates observations by randomly selecting a feature and then 
# randomly selecting a split value. Anomalies typically require fewer splits to be isolated.
model = IsolationForest(contamination='auto', random_state=42)
model.fit(X_train)

print("Predicting anomalies on the full dataset...")
X_all = df[features]

# Output of IsolationForest: 1 for normal, -1 for anomaly
predictions = model.predict(X_all)
# Convert to 0 for normal, 1 for anomaly
df['is_anomaly_pred'] = (predictions == -1).astype(int)

# Anomaly score (lower = more anomalous in sklearn, we can just save it)
df['anomaly_score'] = model.decision_function(X_all)

# Save predictions
out_df = df[['timestamp', 'anomaly_score', 'is_anomaly_pred']]
# Rename column to match lab requirements:
out_df = out_df.rename(columns={'is_anomaly_pred': 'is_anomaly'})

out_file = 'anomaly_predictions.csv'
out_df.to_csv(out_file, index=False)
print(f"Predictions saved to {out_file}")

# Calculate Accuracy against ground truth
# Compare our Isolation Forest unsupervised predictions against what we know was actually an anomaly
gt_anomalies = df['is_anomaly'] # from build_dataset
pred_anomalies = df['is_anomaly_pred']

true_positives = ((gt_anomalies == 1) & (pred_anomalies == 1)).sum()
false_positives = ((gt_anomalies == 0) & (pred_anomalies == 1)).sum()
false_negatives = ((gt_anomalies == 1) & (pred_anomalies == 0)).sum()

print("\n--- Detection Performance ---")
print(f"True Positives (Correctly caught anomaly windows): {true_positives}")
print(f"False Positives (False alarms): {false_positives}")
print(f"False Negatives (Missed anomaly windows): {false_negatives}")

# VISUALIZATION
# Graphing Latency and Error rates over time, highlighting detected anomalies 
# in Red against the Ground Truth window in Orange.
print("\nGenerating Visualizations...")

plt.figure(figsize=(14, 6))
plt.plot(df['timestamp'], df['avg_latency'], label='Avg Latency (ms)', color='blue')
# Highlight predicted anomalies
anomalies = df[df['is_anomaly_pred'] == 1]
plt.scatter(anomalies['timestamp'], anomalies['avg_latency'], color='red', label='Predicted Anomaly', zorder=5)

plt.axvspan(pd.to_datetime(gt['anomaly_start_iso']), pd.to_datetime(gt['anomaly_end_iso']), color='orange', alpha=0.3, label='Ground Truth Window')
plt.title('Latency Timeline with Anomalies')
plt.xlabel('Time')
plt.ylabel('Latency (ms)')
plt.legend()
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.tight_layout()
plt.savefig('latency_timeline.png')
print("Saved latency_timeline.png")

plt.figure(figsize=(14, 6))
plt.plot(df['timestamp'], df['error_rate'] * 100, label='Error Rate (%)', color='purple')
plt.scatter(anomalies['timestamp'], anomalies['error_rate'] * 100, color='red', label='Predicted Anomaly', zorder=5)
plt.axvspan(pd.to_datetime(gt['anomaly_start_iso']), pd.to_datetime(gt['anomaly_end_iso']), color='orange', alpha=0.3, label='Ground Truth Window')
plt.title('Error Rate Timeline with Anomalies')
plt.xlabel('Time')
plt.ylabel('Error Rate (%)')
plt.legend()
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
plt.tight_layout()
plt.savefig('error_rate_timeline.png')
print("Saved error_rate_timeline.png")

print("Done.")
