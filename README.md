# AIOps Observability API

This repository houses a Laravel-based API serving as a testbed for advanced observability and AIOps telemetry. The application emits ML-ready structured logs, exposes Prometheus RED (Rate, Errors, Duration) metrics, and is accompanied by a full monitoring stack capable of detecting controlled anomaly injections.

## System Architecture

The project consists of three main components:

1.  **Laravel API**:
    - Powered by a custom `TelemetryMiddleware` that intercepts every incoming request and outgoing response.
    - Generates a highly structured, stable JSON log schema (found in `storage/logs/aiops.log`) containing standard HTTP context (method, path, user agent, IP), latency calculations, exact payload sizes, and correlation IDs.
    - Utilizes a central `categorizeError` function within the Exception handler to group diverse application faults into easily digestible categories for ML algorithms (`DATABASE_ERROR`, `TIMEOUT_ERROR`, `VALIDATION_ERROR`, `SYSTEM_ERROR`).
    - Exposes a `/metrics` endpoint rendering cumulative histogram buckets for Prometheus scraping.

2.  **Monitoring Stack**:
    - **Prometheus**: Scrapes the `/metrics` endpoint every 5 seconds, capturing throughput, localized error rates, and histogram-based latency metrics.
    - **Grafana**: Provides real-time visualization of the system's health, pre-configured with a dashboard to monitor Request per Second (RPS), Error Percentages, Latency Percentiles (P50/P95/P99), and stacked error breakdowns.

3.  **Traffic Generator**:
    - A multi-threaded Python script (`traffic_generator.py`) capable of simulating sustained base load across all endpoints.
    - Capable of injecting strict, time-bounded anomalies (e.g., an "Error Spike") to validate the monitoring pipeline's detection capabilities.
    - Records actual execution timestamps into a `ground_truth.json` file for comparison against dashboard findings.

## Available API Endpoints

The API is intentionally designed to exhibit various stable and unstable behaviors:

| Endpoint           | Method | Behavior / Failure Mode                                                                                                                                        |
| :----------------- | :----- | :------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/api/normal`      | GET    | Simulates standard, healthy traffic (always returns 200 OK fast).                                                                                              |
| `/api/slow`        | GET    | Simulates API degradation (random sleep between 1-3 seconds).                                                                                                  |
| `/api/slow?hard=1` | GET    | Simulates severe degradation (random sleep between 5-7 seconds). Will trigger a `TIMEOUT_ERROR` classification in logs even on a 200 OK.                       |
| `/api/error`       | GET    | Hardcoded to throw a generic `Exception` (returns 500, logs `SYSTEM_ERROR`).                                                                                   |
| `/api/db`          | GET    | Queries a `dummy_data` table natively.                                                                                                                         |
| `/api/db?fail=1`   | GET    | Forces a database failure by querying a non-existent table (returns 500, logs `DATABASE_ERROR`).                                                               |
| `/api/validate`    | POST   | Expects JSON payload `{"email": "...", "age": X}`. Rejects invalid formats (e.g., age <= 0 or missing fields), returning a 422 and logging `VALIDATION_ERROR`. |

## Getting Started

### 1. Run the Laravel Application

Install dependencies and run the database migrations (required for `/api/db`):

```bash
composer install
php artisan migrate
php artisan serve
```

### 2. Start the Monitoring Features

Ensure Docker is running, then spin up Promtheus and Grafana:

```bash
docker-compose up -d
```

You can view Grafana at `http://localhost:3000` (Default login: `admin` / `admin`).

### 3. Generate Traffic

Run the Python load generator to simulate realistic traffic patterns across the API endpoints:

```bash
python traffic_generator.py
```
