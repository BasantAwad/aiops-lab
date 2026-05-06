import json
import random
import uuid
from datetime import datetime, timedelta

print("Generating synthetic telemetry aligned with ground truth...")

try:
    with open('ground_truth.json', 'r') as f:
        gt = json.load(f)
        anomaly_start = datetime.fromisoformat(gt['anomaly_start_iso'])
except Exception as e:
    print(f"Failed to load ground truth: {e}")
    exit(1)

# Generate 1500 windows (45000 seconds = 12.5 hours) BEFORE the anomaly start
total_windows = 1500
current_ts = anomaly_start - timedelta(seconds=total_windows * 30 + 60) # start way back

new_logs = []
endpoints = ['/api/normal', '/api/slow', '/api/db', '/api/error', '/api/validate']
weights = [0.70, 0.15, 0.05, 0.05, 0.05]

for i in range(total_windows):
    num_reqs = random.randint(100, 150)
    
    for _ in range(num_reqs):
        ep = random.choices(endpoints, weights)[0]
        
        status_code = 200
        error_category = "NONE"
        latency_ms = random.randint(10, 50)
        
        if ep == '/api/slow':
            latency_ms = random.randint(800, 1500)
        elif ep == '/api/db':
            latency_ms = random.randint(30, 100)
        elif ep == '/api/error':
            if random.random() < 0.05:
                status_code = 500
                error_category = "SYSTEM_ERROR"
        elif ep == '/api/validate':
            if random.random() < 0.02:
                status_code = 422
                error_category = "VALIDATION_ERROR"
                
        current_ts += timedelta(seconds=30 / num_reqs)
        
        new_logs.append({
            "timestamp": current_ts.isoformat(),
            "trace_id": str(uuid.uuid4()),
            "method": "GET",
            "path": ep,
            "status_code": status_code,
            "error_category": error_category,
            "latency_ms": latency_ms
        })

print(f"Generated {len(new_logs)} synthetic base-load logs.")

# Now we want to keep the REAL anomaly window from our traffic_generator payload in logs.json
# We'll extract only the logs that happened around or after anomaly_start from existing logs.json
kept_logs = []
try:
    with open('logs.json', 'r') as f:
        # File contains multiple concatenated JSON lines or objects
        content = f.read().strip().replace('}\n{', '},{')
        if not content.startswith('['):
            content = '[' + content + ']'
        existing_logs = json.loads(content)
        
    for log in existing_logs:
        log_ts = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
        if log_ts >= (anomaly_start - timedelta(minutes=5)):
            kept_logs.append(log)
except Exception as e:
    print(f"Failed to filter existing logs: {e}")

print(f"Kept {len(kept_logs)} real recent logs.")

all_logs = new_logs + kept_logs

with open('logs.json', 'w') as f:
    json.dump(all_logs, f, indent=2)
    
print("Saved to logs.json. Now build_dataset.py should perfectly align.")
