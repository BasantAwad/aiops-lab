<p align="center">
  <img src="https://raw.githubusercontent.com/BasantAwad/BasantAwad/main/assets/basant-terminal-banner.png" alt="Terminal-inspired project banner" width="100%" />
</p>

# AIOps Observability Lab

A progressive AIOps platform that moves from telemetry-aware APIs to anomaly detection, root-cause analysis, and automated incident response.

## Learning path

1. Build a Laravel API with structured logs and Prometheus RED metrics.
2. Add rule-based detection for common operational failure modes.
3. Use machine learning to identify anomalous behavior.
4. Perform automated root-cause analysis across telemetry signals.
5. Trigger server-side incident responses from detected conditions.

## Stack

Laravel, PHP, Prometheus, Grafana, Python, Pandas, NumPy, scikit-learn, Matplotlib, Docker Compose.

## Run locally

Install PHP and Composer, Python 3, Docker, and Docker Compose. Follow the lab-specific instructions and start the required services with:

```bash
docker compose up --build
```

The project exposes telemetry and metrics endpoints for local experimentation; do not use the default configuration as a production security baseline.
