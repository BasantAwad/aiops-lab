# AIOps Observability and Detection Labs

This repository contains an end-to-end AIOps project, structured into three progressive labs. We start by building a telemetry-aware API, then implement a rule-based detection engine, and finally use Machine Learning to predict and isolate anomalies.

## Prerequisites
- PHP & Composer
- Docker & Docker Compose
- Python (with dependencies installed)

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
