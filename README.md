# AIOps Observability and Detection Labs

This repository contains an end-to-end AIOps project, structured into five progressive labs. We start by building a telemetry-aware API, implement a rule-based detection engine, use Machine Learning to predict anomalies, perform automated root cause analysis, and finally build an automated incident response system.

## Prerequisites
- PHP & Composer
- Docker & Docker Compose
- Python 3 with `pandas`, `numpy`, `scikit-learn`, `matplotlib`

---

## Lab 1: AIOps Observability

In this lab, we build a Laravel-based API that serves as a testbed for advanced observability. The application emits ML-ready structured logs and exposes Prometheus RED (Rate, Errors, Duration) metrics.

### Features
- **TelemetryMiddleware**: Intercepts requests/responses, calculates latency, and injects correlation IDs. Logs are saved to `storage/logs/aiops.log` in structured JSON format.
- **Centralized Error Categorization**: Groups application faults into categories like `DATABASE_ERROR`, `TIMEOUT_ERROR`, `VALIDATION_ERROR`, and `SYSTEM_ERROR`.
- **Metrics Endpoint**: Exposes a `/metrics` URL for Prometheus scraping.

### Available API Endpoints (Lab 1)
| Endpoint | Method | Behavior / Failure Mode |
| :--- | :--- | :--- |
| `/api/normal` | GET | Simulates standard, healthy traffic (always returns 200 OK fast). |
| `/api/slow` | GET | Simulates API degradation (random sleep between 1-3 seconds). |
| `/api/slow?hard=1` | GET | Simulates severe degradation (random sleep 5-7 seconds) and triggers `TIMEOUT_ERROR`. |
| `/api/error` | GET | Throws a generic Exception (returns 500, logs `SYSTEM_ERROR`). |
| `/api/db` | GET | Queries a `dummy_data` table natively. |
| `/api/db?fail=1` | GET | Forces a database failure (returns 500, logs `DATABASE_ERROR`). |
| `/api/validate` | POST | Expects `{"email": "...", "age": X}`. Rejects invalid formats (logging `VALIDATION_ERROR`). |

### How to Run Lab 1
1. **Start the Database & API:**
   ```bash
   composer install
   php artisan migrate
   php artisan serve
   ```
2. **Start Monitoring Stack (Prometheus + Grafana):**
   ```bash
   docker-compose up -d
   ```
   *(Grafana is available at `http://localhost:3000` with admin/admin).*
   
3. **Generate Traffic & Anomalies:**
   Use the Python load generator to simulate traffic. 
   *(Note: Since your `.venv` is missing an `activate` script, you must run the Python executable directly like this):*
   ```powershell
   .\.venv\Scripts\python.exe traffic_generator.py
   ```
   *(This script will create a `ground_truth.json` file logging the anomaly timestamps).*

---

## Lab 2: AIOps Detection Engine

In this lab, we created an active detection engine. Instead of passive monitoring on dashboards, this engine continuously queries Prometheus strictly to identify anomalies and correlate signals into higher-level incidents, avoiding alert fatigue.

### Features
- **Baseline Modeling**: Dynamically computes average latency, request rates, and error rates using Prometheus.
- **Multi-Signal Detection**: Identifies performance degradation by combining signals (latency + error rates).
- **Incident Generation**: Correlates anomalies and writes structured incidents to `storage/aiops/incidents.json`.

### How to Run Lab 2
1. Ensure the Lab 1 API (`php artisan serve`) and Docker containers are already running.
2. Open a new terminal and start the continuous detection command:
   ```bash
   php artisan aiops:detect
   ```
3. With this running, if you execute the Lab 1 `traffic_generator.py`, the detection engine will pick up the real-time anomaly, output it to the console, and generate standard incidents in `storage/aiops/incidents.json`.

---

## Lab 3: ML Anomaly Detection

We shift from rule-based thresholds to Machine Learning. This lab extracts historical telemetry to train an Unsupervised Machine Learning model that detects anomalous system behavior based solely on observed metrics.

### Features
- **Dataset Generation**: Parses logs and Prometheus metrics into `aiops_dataset.csv`.
- **Feature Engineering**: Calculates rolling averages, error rates, and standard deviations over time windows.
- **Model Training**: Uses an Anomaly Detection model to rank normal vs abnormal operation.

### How to Run Lab 3
1. **Export Logs (Dataset Construction):**
   *(Ensure you have run the traffic generator in Lab 1 sufficiently to generate logs).*
   ```powershell
   .\.venv\Scripts\python.exe build_dataset.py
   ```
2. **Train the ML Model:**
   ```powershell
   .\.venv\Scripts\python.exe train_model.py
   ```
   *(This outputs `anomaly_predictions.csv` and visualization charts like `latency_timeline.png`).*

---

## Lab 4: Root Cause Analysis

With anomalies detected in Labs 2 and 3, this lab determines **why** the anomaly occurred. The RCA engine analyzes metrics and logs to identify the most likely source of the incident.

### Features
- **Incident Selection**: Automatically selects the most significant anomaly cluster from Lab 3 ML predictions.
- **Multi-Signal Analysis**: Compares baseline vs anomaly signals (latency, request rate, error rate, error count, P95 latency).
- **Endpoint Attribution**: Scores each API endpoint using a composite metric (traffic share shift, error rate delta, error volume contribution, latency factor) to determine which endpoint caused the incident.
- **Error Category Analysis**: Breaks down `SYSTEM_ERROR`, `DATABASE_ERROR`, `TIMEOUT_ERROR`, and `VALIDATION_ERROR` distributions during the anomaly window.
- **Incident Timeline**: Constructs a phased timeline (Normal → Anomaly Start → Peak → Recovery).
- **Structured RCA Report**: Generates `rca_report.json` with `incident_id`, `root_cause_endpoint`, `primary_signal`, `supporting_evidence`, `confidence_score`, and `recommended_action`.

### How to Run Lab 4
```powershell
.\.venv\Scripts\python.exe root_cause_analysis.py
```

### Outputs
| File | Description |
| :--- | :--- |
| `rca_report.json` | Structured RCA output (machine-readable) |
| `rca_timeline.png` | 4-panel incident timeline visualization |
| `rca_attribution.png` | Endpoint attribution score chart |
| `RCA_REPORT.md` | 2-page RCA narrative report |

---

## Lab 5: Automated Incident Response

The final step in the AIOps pipeline: automation. The system not only detects incidents but also triggers automatic responses based on configurable policies.

### Features
- **Automation Engine**: Laravel artisan command that monitors incident records and executes policy-based responses.
- **Response Policies**: Defined in `config/aiops.php`, mapping each incident type to specific automated actions.
- **Simulated Actions**: Service restart, traffic throttling, alert dispatch, horizontal scaling, cache flush, circuit breaker activation.
- **Response Logging**: Every action is logged to `storage/aiops/responses.json` with `incident_id`, `action_taken`, `timestamp`, `result`, and `notes`.
- **Escalation Logic**: If automated actions fail or anomalies persist beyond `max_retries`, the engine escalates to `CRITICAL_ALERT` (notifying ops-manager, sre-lead via pagerduty).
- **Cooldown Deduplication**: Prevents action flooding by enforcing cooldown periods per incident type + endpoint combination.

### Response Policies

| Incident Type | Automated Actions | Escalation |
| :--- | :--- | :--- |
| `LATENCY_SPIKE` | restart_service, flush_cache | CRITICAL_ALERT |
| `ERROR_STORM` | send_alert, throttle_traffic | CRITICAL_ALERT |
| `TRAFFIC_SURGE` | scale_service, enable_queue | CRITICAL_ALERT |
| `SERVICE_DEGRADATION` | send_alert, restart_service, throttle_traffic | CRITICAL_ALERT |

### How to Run Lab 5
```bash
# Single response cycle (process all open incidents once)
php artisan aiops:respond --once

# Continuous monitoring mode
php artisan aiops:respond

# Dry run (simulate without writing logs)
php artisan aiops:respond --once --dry-run
```

### Outputs
| File | Description |
| :--- | :--- |
| `storage/aiops/responses.json` | Automated response log with all action records |
| `config/aiops.php` | Response policy configuration |
| `LAB5_REPORT.md` | Engineering report |

---

## Project Structure

```
aiops-lab/
├── app/Console/Commands/
│   ├── RunAIOpsDetection.php      # Lab 2 — Detection engine
│   └── RunAIOpsResponse.php       # Lab 5 — Automated response engine
├── app/Services/
│   └── PrometheusClient.php       # Prometheus query client
├── config/
│   └── aiops.php                  # Lab 5 — Response policies
├── storage/aiops/
│   ├── incidents.json             # Lab 2 — Detected incidents
│   └── responses.json             # Lab 5 — Automated response logs
├── traffic_generator.py           # Lab 1 — Traffic & anomaly injection
├── build_dataset.py               # Lab 3 — Dataset construction
├── train_model.py                 # Lab 3 — ML model training
├── root_cause_analysis.py         # Lab 4 — RCA engine
├── rca_report.json                # Lab 4 — Structured RCA output
├── ground_truth.json              # Lab 1 — Anomaly timestamps
├── ENGINEERING_REPORT.md          # Lab 2 — Detection engine report
├── ML_REPORT.md                   # Lab 3 — ML model report
├── RCA_REPORT.md                  # Lab 4 — Root cause analysis report
└── LAB5_REPORT.md                 # Lab 5 — Automation engine report
```
