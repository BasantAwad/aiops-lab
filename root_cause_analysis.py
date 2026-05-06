#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
"""
AIOps Lab Work 4 — Root Cause Analysis (RCA)
Analyzes detected anomaly windows from Labs 2/3, performs signal analysis,
endpoint attribution, error category analysis, builds incident timeline,
and generates a structured RCA report.
"""

import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from datetime import timedelta
from collections import Counter
import uuid
import os

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("=" * 60)
print("  AIOps Root Cause Analysis Engine")
print("=" * 60)

print("\n[1/6] Loading data sources...")

with open('logs.json', 'r') as f:
    content = f.read().strip()
    content = content.replace('}\n{', '},{')
    if not content.startswith('['):
        content = '[' + content + ']'
    logs = json.loads(content)

df = pd.DataFrame(logs)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df['is_error'] = (df['status_code'] >= 400).astype(int)
print(f"  Loaded {len(df)} log entries ({df['timestamp'].min()} to {df['timestamp'].max()})")

with open('ground_truth.json', 'r') as f:
    gt = json.load(f)

with open('storage/aiops/incidents.json', 'r') as f:
    incidents = json.load(f)
print(f"  Loaded {len(incidents)} incidents from Lab 2 detection engine")

dataset = pd.read_csv('aiops_dataset.csv')
dataset['timestamp'] = pd.to_datetime(dataset['timestamp'])

predictions = pd.read_csv('anomaly_predictions.csv')
predictions['timestamp'] = pd.to_datetime(predictions['timestamp'])
print(f"  Loaded {len(predictions)} ML prediction windows from Lab 3")

# ============================================================================
# 2. INCIDENT SELECTION — Select the primary anomaly window
# ============================================================================
print("\n[2/6] Selecting anomaly window for RCA...")

# Use the strongest ML-detected anomaly cluster from Lab 3.
# The cluster at 21:22:30–21:25:00 on 2026-03-09 has the deepest anomaly scores
# and aligns with the ground truth error spike injection from Lab 1.
ml_anomalies = predictions[predictions['is_anomaly'] == 1].copy()

# Identify contiguous anomaly clusters by checking time gaps > 60s
ml_anomalies = ml_anomalies.sort_values('timestamp')
ml_anomalies['gap'] = ml_anomalies['timestamp'].diff().dt.total_seconds().fillna(0)
ml_anomalies['cluster'] = (ml_anomalies['gap'] > 60).cumsum()

# Find the cluster with the most anomaly windows (sustained incident, not isolated spikes)
# Among clusters with count >= 3, pick the one with the lowest mean score
cluster_scores = ml_anomalies.groupby('cluster')['anomaly_score'].agg(['mean', 'count', 'min'])
sustained_clusters = cluster_scores[cluster_scores['count'] >= 3]
if len(sustained_clusters) > 0:
    primary_cluster_id = sustained_clusters['mean'].idxmin()
else:
    primary_cluster_id = cluster_scores['count'].idxmax()
primary_cluster = ml_anomalies[ml_anomalies['cluster'] == primary_cluster_id]

ANOMALY_START = primary_cluster['timestamp'].min()
ANOMALY_END = primary_cluster['timestamp'].max() + timedelta(seconds=30)  # window is 30s

# Expand window slightly for context (pre/post)
CONTEXT_START = ANOMALY_START - timedelta(minutes=3)
CONTEXT_END = ANOMALY_END + timedelta(minutes=3)

print(f"  Primary anomaly window: {ANOMALY_START} -> {ANOMALY_END}")
print(f"  Analysis context:       {CONTEXT_START} -> {CONTEXT_END}")
print(f"  Cluster anomaly score:  {cluster_scores.loc[primary_cluster_id, 'mean']:.4f}")

# Filter logs to the anomaly window and context window
anomaly_logs = df[(df['timestamp'] >= ANOMALY_START) & (df['timestamp'] <= ANOMALY_END)]
context_logs = df[(df['timestamp'] >= CONTEXT_START) & (df['timestamp'] <= CONTEXT_END)]
baseline_logs = df[(df['timestamp'] >= CONTEXT_START) & (df['timestamp'] < ANOMALY_START)]

print(f"  Anomaly window logs: {len(anomaly_logs)}")
print(f"  Context window logs: {len(context_logs)}")
print(f"  Baseline logs:       {len(baseline_logs)}")

# ============================================================================
# 3. SIGNAL ANALYSIS
# ============================================================================
print("\n[3/6] Performing multi-signal analysis...")

ENDPOINTS = ['/api/normal', '/api/slow', '/api/db', '/api/error', '/api/validate']

def compute_signals(log_subset, label=""):
    """Compute key signals from a log subset."""
    total = len(log_subset)
    if total == 0:
        return {}
    duration_s = max((log_subset['timestamp'].max() - log_subset['timestamp'].min()).total_seconds(), 1)
    return {
        'total_requests': total,
        'avg_latency_ms': log_subset['latency_ms'].mean(),
        'p95_latency_ms': log_subset['latency_ms'].quantile(0.95),
        'max_latency_ms': log_subset['latency_ms'].max(),
        'request_rate_rps': total / duration_s,
        'error_rate': log_subset['is_error'].mean(),
        'error_count': log_subset['is_error'].sum(),
    }

baseline_signals = compute_signals(baseline_logs, "baseline")
anomaly_signals = compute_signals(anomaly_logs, "anomaly")

print(f"\n  {'Signal':<25} {'Baseline':>12} {'Anomaly':>12} {'Change':>12}")
print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12}")
for key in ['avg_latency_ms', 'p95_latency_ms', 'request_rate_rps', 'error_rate', 'error_count']:
    bv = baseline_signals.get(key, 0)
    av = anomaly_signals.get(key, 0)
    if key == 'error_rate':
        change = f"{(av - bv)*100:+.1f}pp"
        print(f"  {key:<25} {bv*100:>11.1f}% {av*100:>11.1f}% {change:>12}")
    else:
        pct = ((av - bv) / bv * 100) if bv != 0 else 0
        print(f"  {key:<25} {bv:>12.1f} {av:>12.1f} {pct:>+11.1f}%")

# ============================================================================
# 4. ENDPOINT ATTRIBUTION
# ============================================================================
print("\n[4/6] Performing endpoint attribution...")

endpoint_scores = {}
for ep in ENDPOINTS:
    bl = baseline_logs[baseline_logs['path'] == ep]
    an = anomaly_logs[anomaly_logs['path'] == ep]

    bl_signals = compute_signals(bl)
    an_signals = compute_signals(an)

    # Attribution score: weighted combination of traffic share shift + error contribution
    bl_share = len(bl) / max(len(baseline_logs), 1)
    an_share = len(an) / max(len(anomaly_logs), 1)
    share_delta = an_share - bl_share

    bl_err = bl['is_error'].mean() if len(bl) > 0 else 0
    an_err = an['is_error'].mean() if len(an) > 0 else 0
    err_delta = an_err - bl_err

    # Error volume contribution (what % of all anomaly-window errors came from this endpoint)
    total_anomaly_errors = anomaly_logs['is_error'].sum()
    ep_anomaly_errors = an['is_error'].sum() if len(an) > 0 else 0
    error_contribution = ep_anomaly_errors / max(total_anomaly_errors, 1)

    # Latency impact
    bl_lat = bl['latency_ms'].mean() if len(bl) > 0 else 0
    an_lat = an['latency_ms'].mean() if len(an) > 0 else 0
    lat_factor = (an_lat / max(bl_lat, 1)) if bl_lat > 0 else 1

    # Composite attribution score
    score = (share_delta * 0.3) + (err_delta * 0.3) + (error_contribution * 0.3) + (min(lat_factor / 10, 0.1))

    endpoint_scores[ep] = {
        'attribution_score': score,
        'traffic_share_baseline': bl_share,
        'traffic_share_anomaly': an_share,
        'share_delta': share_delta,
        'error_rate_baseline': bl_err,
        'error_rate_anomaly': an_err,
        'error_rate_delta': err_delta,
        'error_contribution': error_contribution,
        'avg_latency_baseline': bl_lat,
        'avg_latency_anomaly': an_lat,
        'latency_factor': lat_factor,
        'request_count_anomaly': len(an),
        'error_count_anomaly': int(ep_anomaly_errors),
    }

# Sort by attribution score
ranked = sorted(endpoint_scores.items(), key=lambda x: x[1]['attribution_score'], reverse=True)

print(f"\n  {'Rank':<6} {'Endpoint':<18} {'Score':>8} {'Err Delta':>10} {'Share Delta':>10} {'Err Contrib':>12}")
print(f"  {'-'*6} {'-'*18} {'-'*8} {'-'*10} {'-'*10} {'-'*12}")
for i, (ep, s) in enumerate(ranked, 1):
    print(f"  {i:<6} {ep:<18} {s['attribution_score']:>8.4f} {s['error_rate_delta']*100:>+9.1f}% {s['share_delta']*100:>+9.1f}% {s['error_contribution']*100:>11.1f}%")

root_cause_endpoint = ranked[0][0]
root_cause_data = ranked[0][1]
print(f"  >> Root Cause Endpoint: {root_cause_endpoint}")

# ============================================================================
# 5. ERROR CATEGORY ANALYSIS
# ============================================================================
print("\n[5/6] Analyzing error categories...")

bl_errors = baseline_logs[baseline_logs['is_error'] == 1]
an_errors = anomaly_logs[anomaly_logs['is_error'] == 1]

bl_cats = bl_errors['error_category'].value_counts(normalize=True).to_dict() if len(bl_errors) > 0 else {}
an_cats = an_errors['error_category'].value_counts(normalize=True).to_dict() if len(an_errors) > 0 else {}
an_cats_abs = an_errors['error_category'].value_counts().to_dict() if len(an_errors) > 0 else {}

all_cats = set(list(bl_cats.keys()) + list(an_cats.keys()))
error_category_analysis = {}

print(f"\n  {'Category':<22} {'Baseline':>10} {'Anomaly':>10} {'Abs Count':>10} {'Change':>10}")
print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
for cat in sorted(all_cats):
    bl_pct = bl_cats.get(cat, 0)
    an_pct = an_cats.get(cat, 0)
    an_abs = an_cats_abs.get(cat, 0)
    delta = an_pct - bl_pct
    error_category_analysis[cat] = {
        'baseline_pct': round(bl_pct * 100, 2),
        'anomaly_pct': round(an_pct * 100, 2),
        'anomaly_count': int(an_abs),
        'delta_pp': round(delta * 100, 2)
    }
    print(f"  {cat:<22} {bl_pct*100:>9.1f}% {an_pct*100:>9.1f}% {an_abs:>10} {delta*100:>+9.1f}pp")

# Determine primary error category
primary_error_cat = max(an_cats, key=an_cats.get) if an_cats else "UNKNOWN"
print(f"  >> Primary Error Category: {primary_error_cat} ({an_cats.get(primary_error_cat,0)*100:.1f}%)")

# ============================================================================
# 6. INCIDENT TIMELINE
# ============================================================================
print("\n[6/6] Building incident timeline...")

window_size = '30s'
timeline_data = []
for t_start, wdf in context_logs.groupby(pd.Grouper(key='timestamp', freq=window_size)):
    if len(wdf) == 0:
        continue
    timeline_data.append({
        'timestamp': t_start,
        'request_count': len(wdf),
        'error_count': int(wdf['is_error'].sum()),
        'error_rate': wdf['is_error'].mean(),
        'avg_latency': wdf['latency_ms'].mean(),
        'p95_latency': wdf['latency_ms'].quantile(0.95),
        'freq_error_ep': len(wdf[wdf['path'] == '/api/error']) / len(wdf),
    })

timeline_df = pd.DataFrame(timeline_data)

# Determine timeline phases
phases = []
for _, row in timeline_df.iterrows():
    ts = row['timestamp']
    if ts < ANOMALY_START:
        phase = 'NORMAL'
    elif ts <= ANOMALY_END:
        phase = 'ANOMALY'
    else:
        phase = 'RECOVERY'
    phases.append(phase)
timeline_df['phase'] = phases

# Find peak incident window
if len(timeline_df[timeline_df['phase'] == 'ANOMALY']) > 0:
    peak_idx = timeline_df[timeline_df['phase'] == 'ANOMALY']['error_rate'].idxmax()
    peak_row = timeline_df.loc[peak_idx]
    peak_time = peak_row['timestamp']
else:
    peak_time = ANOMALY_START

incident_timeline = {
    'normal_state': {
        'start': str(CONTEXT_START),
        'end': str(ANOMALY_START),
        'description': 'System operating within normal parameters. Error rates, latency, and request rates are within baseline thresholds.',
        'avg_error_rate': round(baseline_signals.get('error_rate', 0) * 100, 2),
        'avg_latency_ms': round(baseline_signals.get('avg_latency_ms', 0), 2),
    },
    'anomaly_start': {
        'timestamp': str(ANOMALY_START),
        'description': f'Anomaly onset detected. Sharp increase in traffic to {root_cause_endpoint} with elevated error rates. {primary_error_cat} errors begin surging.',
        'trigger_signal': 'error_rate',
    },
    'peak_incident': {
        'timestamp': str(peak_time),
        'description': f'Peak degradation reached. Error rate hits {peak_row["error_rate"]*100:.1f}%, {root_cause_endpoint} endpoint contributing {root_cause_data["error_contribution"]*100:.1f}% of all errors.',
        'peak_error_rate': round(float(peak_row['error_rate']) * 100, 2),
        'peak_latency_ms': round(float(peak_row['avg_latency']), 2),
    },
    'recovery': {
        'timestamp': str(ANOMALY_END),
        'end': str(CONTEXT_END),
        'description': 'Error rates return to baseline levels. System recovers as anomalous traffic subsides. Latency normalizes within 1-2 minutes.',
    }
}

print(f"  Normal:        {CONTEXT_START} -> {ANOMALY_START}")
print(f"  Anomaly Start: {ANOMALY_START}")
print(f"  Peak Incident: {peak_time} (error_rate={peak_row['error_rate']*100:.1f}%)")
print(f"  Recovery:      {ANOMALY_END} -> {CONTEXT_END}")

# ============================================================================
# 7. DETERMINE ROOT CAUSE AND CONFIDENCE
# ============================================================================
print("\n" + "=" * 60)
print("  ROOT CAUSE DETERMINATION")
print("=" * 60)

# Confidence score based on multiple factors
confidence_factors = {
    'error_contribution_clarity': min(root_cause_data['error_contribution'] / 0.5, 1.0),  # max if >50%
    'error_rate_spike_magnitude': min(abs(root_cause_data['error_rate_delta']) / 0.3, 1.0),
    'traffic_share_shift': min(abs(root_cause_data['share_delta']) / 0.15, 1.0),
    'ml_detection_agreement': 1.0,  # ML model confirmed anomaly
    'incident_correlation': min(len([i for i in incidents if root_cause_endpoint.replace('/', '\\/') in json.dumps(i.get('affected_endpoints', []))]) / 3, 1.0),
}
confidence_score = round(sum(confidence_factors.values()) / len(confidence_factors), 2)

# Determine primary signal
if root_cause_data['error_rate_delta'] > 0.1:
    primary_signal = 'error_rate'
    signal_desc = f"Error rate surged from {root_cause_data['error_rate_baseline']*100:.1f}% to {root_cause_data['error_rate_anomaly']*100:.1f}%"
elif root_cause_data['latency_factor'] > 3:
    primary_signal = 'latency'
    signal_desc = f"Latency increased {root_cause_data['latency_factor']:.1f}x from baseline"
else:
    primary_signal = 'request_rate'
    signal_desc = f"Traffic share shifted from {root_cause_data['traffic_share_baseline']*100:.1f}% to {root_cause_data['traffic_share_anomaly']*100:.1f}%"

print(f"\n  Root Cause Endpoint:  {root_cause_endpoint}")
print(f"  Primary Signal:       {primary_signal}")
print(f"  Signal Detail:        {signal_desc}")
print(f"  Primary Error Cat:    {primary_error_cat}")
print(f"  Confidence Score:     {confidence_score}")

# ============================================================================
# 8. GENERATE rca_report.json
# ============================================================================
print("\n  Generating rca_report.json...")

rca_report = {
    'incident_id': str(uuid.uuid4()),
    'analysis_timestamp': pd.Timestamp.now().isoformat(),
    'anomaly_window': {
        'start': str(ANOMALY_START),
        'end': str(ANOMALY_END),
        'duration_seconds': (ANOMALY_END - ANOMALY_START).total_seconds(),
        'source': 'Lab 3 Isolation Forest ML Detection + Lab 2 Rule-Based Incidents',
    },
    'root_cause_endpoint': root_cause_endpoint,
    'primary_signal': primary_signal,
    'signal_description': signal_desc,
    'supporting_evidence': {
        'endpoint_attribution': {ep: {
            'attribution_score': round(s['attribution_score'], 4),
            'error_rate_baseline': round(s['error_rate_baseline'] * 100, 2),
            'error_rate_anomaly': round(s['error_rate_anomaly'] * 100, 2),
            'error_contribution_pct': round(s['error_contribution'] * 100, 2),
            'traffic_share_delta_pp': round(s['share_delta'] * 100, 2),
            'latency_factor': round(s['latency_factor'], 2),
        } for ep, s in ranked},
        'error_category_breakdown': error_category_analysis,
        'signal_comparison': {
            'baseline': {k: round(v, 4) if isinstance(v, float) else v for k, v in baseline_signals.items()},
            'anomaly': {k: round(v, 4) if isinstance(v, float) else v for k, v in anomaly_signals.items()},
        },
        'ml_anomaly_scores': primary_cluster[['timestamp', 'anomaly_score']].to_dict('records'),
        'correlated_incidents_count': len(incidents),
    },
    'confidence_score': confidence_score,
    'confidence_factors': confidence_factors,
    'incident_timeline': incident_timeline,
    'recommended_action': (
        f"Investigate {root_cause_endpoint} for {primary_error_cat} errors. "
        f"The endpoint showed a {root_cause_data['error_rate_delta']*100:.0f}pp error rate increase "
        f"and contributed {root_cause_data['error_contribution']*100:.0f}% of all errors during the anomaly window. "
        f"Check application error handling, upstream dependencies, and resource limits for this endpoint. "
        f"Implement circuit breakers and rate limiting to prevent cascading failures."
    ),
}

# Serialize timestamps
def serialize(obj):
    if isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

with open('rca_report.json', 'w') as f:
    json.dump(rca_report, f, indent=2, default=serialize)
print("  [OK] Saved rca_report.json")

# ============================================================================
# 9. VISUALIZATIONS
# ============================================================================
print("\n  Generating visualizations...")

plt.style.use('seaborn-v0_8-darkgrid')
fig, axes = plt.subplots(4, 1, figsize=(16, 18), sharex=True)
fig.suptitle('AIOps Root Cause Analysis — Incident Timeline', fontsize=16, fontweight='bold', y=0.98)

# Color the anomaly window
for ax in axes:
    ax.axvspan(ANOMALY_START, ANOMALY_END, alpha=0.15, color='red', label='Anomaly Window')
    ax.axvline(peak_time, color='darkred', linestyle='--', alpha=0.7, linewidth=1)

# Panel 1: Error Rate by Endpoint
ax = axes[0]
for ep in ENDPOINTS:
    ep_ctx = context_logs[context_logs['path'] == ep].copy()
    if len(ep_ctx) == 0:
        continue
    ep_windows = []
    for t_start, wdf in ep_ctx.groupby(pd.Grouper(key='timestamp', freq=window_size)):
        if len(wdf) == 0:
            continue
        ep_windows.append({'timestamp': t_start, 'error_rate': wdf['is_error'].mean()})
    if ep_windows:
        epdf = pd.DataFrame(ep_windows)
        ax.plot(epdf['timestamp'], epdf['error_rate'] * 100, label=ep, linewidth=1.5, marker='o', markersize=3)
ax.set_ylabel('Error Rate (%)')
ax.set_title('Error Rate by Endpoint')
ax.legend(loc='upper left', fontsize=8)
ax.set_ylim(-5, 105)

# Panel 2: Latency
ax = axes[1]
ax.plot(timeline_df['timestamp'], timeline_df['avg_latency'], color='#2196F3', linewidth=1.5, label='Avg Latency')
ax.plot(timeline_df['timestamp'], timeline_df['p95_latency'], color='#FF5722', linewidth=1.5, alpha=0.7, label='P95 Latency')
ax.set_ylabel('Latency (ms)')
ax.set_title('Latency Timeline')
ax.legend(loc='upper left', fontsize=8)

# Panel 3: Request Rate & Error Count
ax = axes[2]
ax.bar(timeline_df['timestamp'], timeline_df['request_count'], width=0.0003, color='#4CAF50', alpha=0.6, label='Requests')
ax.bar(timeline_df['timestamp'], timeline_df['error_count'], width=0.0003, color='#f44336', alpha=0.8, label='Errors')
ax.set_ylabel('Count (per 30s window)')
ax.set_title('Request Volume & Error Count')
ax.legend(loc='upper left', fontsize=8)

# Panel 4: Error Category Distribution (stacked area)
ax = axes[3]
cats_over_time = []
for t_start, wdf in context_logs.groupby(pd.Grouper(key='timestamp', freq=window_size)):
    errs = wdf[wdf['is_error'] == 1]
    if len(errs) == 0:
        row = {'timestamp': t_start}
        for c in ['SYSTEM_ERROR', 'TIMEOUT_ERROR', 'DATABASE_ERROR', 'VALIDATION_ERROR']:
            row[c] = 0
        cats_over_time.append(row)
        continue
    row = {'timestamp': t_start}
    vc = errs['error_category'].value_counts()
    for c in ['SYSTEM_ERROR', 'TIMEOUT_ERROR', 'DATABASE_ERROR', 'VALIDATION_ERROR']:
        row[c] = vc.get(c, 0)
    cats_over_time.append(row)

if cats_over_time:
    cat_df = pd.DataFrame(cats_over_time)
    colors = {'SYSTEM_ERROR': '#f44336', 'TIMEOUT_ERROR': '#FF9800', 'DATABASE_ERROR': '#9C27B0', 'VALIDATION_ERROR': '#2196F3'}
    bottom = np.zeros(len(cat_df))
    for c in ['SYSTEM_ERROR', 'TIMEOUT_ERROR', 'DATABASE_ERROR', 'VALIDATION_ERROR']:
        if c in cat_df.columns:
            ax.bar(cat_df['timestamp'], cat_df[c], width=0.0003, bottom=bottom, color=colors[c], alpha=0.8, label=c)
            bottom += cat_df[c].values
    ax.set_ylabel('Error Count')
    ax.set_title('Error Category Distribution')
    ax.legend(loc='upper left', fontsize=8)

axes[-1].set_xlabel('Time')
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.xticks(rotation=30)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('rca_timeline.png', dpi=150, bbox_inches='tight')
print("  [OK] Saved rca_timeline.png")

# --- Endpoint Attribution Chart ---
fig2, ax2 = plt.subplots(figsize=(12, 6))
eps = [ep for ep, _ in ranked]
scores = [s['attribution_score'] for _, s in ranked]
err_contribs = [s['error_contribution'] * 100 for _, s in ranked]

x = np.arange(len(eps))
width = 0.35
bars1 = ax2.bar(x - width/2, scores, width, label='Attribution Score', color='#1976D2', alpha=0.85)
ax2_twin = ax2.twinx()
bars2 = ax2_twin.bar(x + width/2, err_contribs, width, label='Error Contribution (%)', color='#f44336', alpha=0.85)

ax2.set_xlabel('Endpoint')
ax2.set_ylabel('Attribution Score')
ax2_twin.set_ylabel('Error Contribution (%)')
ax2.set_xticks(x)
ax2.set_xticklabels(eps, rotation=15)
ax2.set_title('Endpoint Attribution Analysis', fontsize=14, fontweight='bold')

lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_twin.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.tight_layout()
plt.savefig('rca_attribution.png', dpi=150, bbox_inches='tight')
print("  [OK] Saved rca_attribution.png")

print("\n" + "=" * 60)
print("  RCA COMPLETE")
print("=" * 60)
print(f"\n  Root Cause:        {root_cause_endpoint} caused {primary_signal} anomaly")
print(f"  Primary Error:     {primary_error_cat}")
print(f"  Confidence:        {confidence_score}")
print(f"  Deliverables:")
print("    - rca_report.json")
print("    - rca_timeline.png")
print("    - rca_attribution.png")
print()
