# AIOps Lab 1: Observability & Telemetry

This repository contains the complete implementation for **AIOps Lab Work 1**. It features a Laravel API emitting ML-ready telemetry, a Prometheus/Grafana monitoring stack, and a custom traffic generator that injects a controlled anomaly (error spike).

## Deliverables Included

1.  **Codebase:** The complete Laravel application with the modified `TelemetryMiddleware.php` and centralized exception handling in `Handler.php`.
2.  **Logs:**
    - `storage/logs/aiops.log`: The raw structured JSON logs (≥ 4,100 entries).
    - `logs.json`: The exported and validated dataset (≥ 1,500 entries, ≥ 100 errors).
3.  **Metrics:**
    - A working `/metrics` endpoint exposing Prometheus RED (Rate, Errors, Duration) metrics.
4.  **Monitoring Stack:**
    - `docker-compose.yml` and `prometheus.yml` for automated setup.
5.  **Dashboarding:**
    - Pre-provisioned Grafana dashboard (`grafana/dashboards/aiops-dashboard.json`) containing the 5 required panels.
    - Screenshots demonstrating the anomaly spike are gathered in the `snapshots/` directory and embedded in the Engineering Report.
6.  **Traffic Generation:**
    - `traffic_generator.py`: A threaded script orchestrating base load, an anomaly window (error spike), and a post-anomaly recovery phase.
    - `ground_truth.json`: Contains the exact UTC timestamps of the 2-minute anomaly window.
7.  **Documentation:**
    - `engineering_report.md`: The 2-3 page Engineering Report detailing log schema design, metrics implementation, anomaly control, and visual proof of the system reacting to the traffic spikes.

## Setup & Execution

### 1. Start the API

```bash
composer install
php artisan migrate
php artisan serve
```

### 2. Start the Monitoring Stack

```bash
docker-compose up -d
```

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin / admin)

### 3. Generate Traffic & Anomalies

Run the Python traffic generator to simulate ~12 minutes of traffic natively:

```bash
python traffic_generator.py
```

This script handles the base load, injects a 40% error spike for exactly 2 minutes, and recovers. It automatically generates the `ground_truth.json` file.

### 4. Export the Dataset

```bash
python export_logs.py
```

This reads `storage/logs/aiops.log` and outputs the validated `logs.json`.
