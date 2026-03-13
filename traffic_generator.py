#!/usr/bin/env python3
"""
AIOps Traffic Generator — Controlled experiment with ground truth anomaly injection.

Base load: ~10 minutes, >=3000 requests
Anomaly window: exactly 2 minutes (error spike)
Outputs: ground_truth.json
"""

import requests
import random
import time
import json
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000/api"

# ── Distribution config ──────────────────────────────────────────
NORMAL_DISTRIBUTION = {
    "normal":        0.70,
    "slow":          0.15,
    "slow_hard":     0.05,
    "error":         0.05,
    "db":            0.03,
    "validate":      0.02,
}

ANOMALY_DISTRIBUTION = {
    "normal":        0.40,
    "slow":          0.10,
    "slow_hard":     0.05,
    "error":         0.40,   # Error spike: 40% (between 35-50%)
    "db":            0.03,
    "validate":      0.02,
}

# ── Timing config ────────────────────────────────────────────────
BASE_DURATION_SECONDS    = 1 * 60    # 1 minute base load
ANOMALY_DURATION_SECONDS = 1 * 60    # 1 minute anomaly window
POST_ANOMALY_SECONDS     = 1 * 60    # 1 minute post-anomaly
TOTAL_MIN_REQUESTS       = 3000
TARGET_RPS               = 6         # Requests dispatched per second
MAX_WORKERS              = 15        # Concurrent threads for slow requests


def pick_endpoint(distribution):
    """Weighted random selection based on distribution dict."""
    r = random.random()
    cumulative = 0.0
    for endpoint, weight in distribution.items():
        cumulative += weight
        if r <= cumulative:
            return endpoint
    return "normal"


def make_request(endpoint, session):
    """Send a single request to the chosen endpoint. Returns (endpoint, status_code)."""
    headers = {"X-Request-Id": "tg-" + str(random.randint(100000, 999999))}

    try:
        if endpoint == "normal":
            r = session.get(BASE_URL + "/normal", headers=headers, timeout=15)

        elif endpoint == "slow":
            r = session.get(BASE_URL + "/slow", headers=headers, timeout=15)

        elif endpoint == "slow_hard":
            r = session.get(BASE_URL + "/slow?hard=1", headers=headers, timeout=15)

        elif endpoint == "error":
            r = session.get(BASE_URL + "/error", headers=headers, timeout=15)

        elif endpoint == "db":
            fail = "?fail=1" if random.random() < 0.2 else ""
            r = session.get(BASE_URL + "/db" + fail, headers=headers, timeout=15)

        elif endpoint == "validate":
            if random.random() < 0.5:
                payload = {"email": "invalid-email", "age": random.choice([5, 0, -1, 100])}
            else:
                payload = {"email": "user" + str(random.randint(1, 999)) + "@example.com", "age": random.randint(18, 60)}
            r = session.post(BASE_URL + "/validate", json=payload, headers=headers, timeout=15)

        else:
            r = session.get(BASE_URL + "/normal", headers=headers, timeout=15)

        return (endpoint, r.status_code)
    except requests.exceptions.Timeout:
        return (endpoint, 408)
    except requests.exceptions.ConnectionError:
        return (endpoint, 503)
    except Exception:
        return (endpoint, 500)


def run_phase(name, duration_seconds, distribution, stats, executor):
    """Run a traffic phase for the given duration using thread pool."""
    print("")
    print("=" * 60)
    print("  Phase: " + name)
    print("  Duration: " + str(duration_seconds) + "s | Target RPS: ~" + str(TARGET_RPS))
    dist_str = ", ".join(k + ": " + str(int(v * 100)) + "%" for k, v in distribution.items())
    print("  Distribution: {" + dist_str + "}")
    print("=" * 60)

    start = time.time()
    phase_count = 0
    futures = []
    sleep_interval = 1.0 / TARGET_RPS

    # Use a thread-safe session per thread via thread-local
    session = requests.Session()

    while time.time() - start < duration_seconds:
        endpoint = pick_endpoint(distribution)
        future = executor.submit(make_request, endpoint, session)
        futures.append(future)
        phase_count += 1
        stats["total"] += 1
        stats["by_endpoint"][endpoint] = stats["by_endpoint"].get(endpoint, 0) + 1

        # Progress every 100 requests dispatched
        if stats["total"] % 100 == 0:
            elapsed = time.time() - stats["global_start"]
            actual_rps = stats["total"] / elapsed if elapsed > 0 else 0
            print("  [" + name + "] Dispatched: " + str(stats["total"]) + " | RPS: " + "{:.1f}".format(actual_rps))

        # Jitter the dispatch rate slightly
        time.sleep(sleep_interval * random.uniform(0.7, 1.3))

    # Collect results from this phase
    for future in as_completed(futures):
        try:
            endpoint, status = future.result(timeout=15)
            if status >= 400:
                stats["errors"] += 1
        except Exception:
            stats["errors"] += 1

    print("  [" + name + "] Phase complete — " + str(phase_count) + " requests dispatched")


def main():
    print("=" * 60)
    print("  AIOps Traffic Generator")
    print("  Target: " + BASE_URL)
    print("  Target RPS: ~" + str(TARGET_RPS))
    total_dur = BASE_DURATION_SECONDS + ANOMALY_DURATION_SECONDS + POST_ANOMALY_SECONDS
    print("  Total duration: ~" + str(total_dur) + "s (" + str(total_dur // 60) + " min)")
    print("=" * 60)

    # Verify server is reachable
    try:
        r = requests.get(BASE_URL + "/normal", timeout=5)
        print("  Server check: " + str(r.status_code) + " — OK")
    except Exception as e:
        print("  ERROR: Cannot reach server at " + BASE_URL)
        print("  " + str(e))
        print("  Make sure `php artisan serve` is running!")
        sys.exit(1)

    stats = {
        "total": 0,
        "errors": 0,
        "by_endpoint": {},
        "global_start": time.time(),
    }

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    # ── Phase 1: Base load ────────────────────────────────────────
    run_phase("BASE LOAD", BASE_DURATION_SECONDS, NORMAL_DISTRIBUTION, stats, executor)

    # ── Phase 2: Anomaly window (exactly 2 minutes) ──────────────
    anomaly_start = datetime.now(timezone.utc)
    anomaly_start_iso = anomaly_start.isoformat()
    print("")
    print("  >>> ANOMALY INJECTION START: " + anomaly_start_iso)

    run_phase("ANOMALY (Error Spike)", ANOMALY_DURATION_SECONDS, ANOMALY_DISTRIBUTION, stats, executor)

    anomaly_end = datetime.now(timezone.utc)
    anomaly_end_iso = anomaly_end.isoformat()
    print("  >>> ANOMALY INJECTION END: " + anomaly_end_iso)

    # ── Phase 3: Post-anomaly (back to normal) ────────────────────
    run_phase("POST-ANOMALY", POST_ANOMALY_SECONDS, NORMAL_DISTRIBUTION, stats, executor)

    executor.shutdown(wait=True)

    # ── Results ──────────────────────────────────────────────────
    total_time = time.time() - stats["global_start"]
    print("")
    print("=" * 60)
    print("  RESULTS")
    print("  Total requests: " + str(stats["total"]))
    print("  Total errors:   " + str(stats["errors"]))
    print("  Duration:       " + "{:.1f}".format(total_time) + "s")
    print("  Avg RPS:        " + "{:.1f}".format(stats["total"] / total_time))
    print("  By endpoint:")
    for k, v in stats["by_endpoint"].items():
        print("    " + k + ": " + str(v))
    print("=" * 60)

    if stats["total"] < TOTAL_MIN_REQUESTS:
        print("")
        print("  WARNING: Only " + str(stats["total"]) + " requests sent (need >=" + str(TOTAL_MIN_REQUESTS) + ")")

    # ── Ground Truth ─────────────────────────────────────────────
    ground_truth = {
        "anomaly_start_iso": anomaly_start_iso,
        "anomaly_end_iso": anomaly_end_iso,
        "anomaly_type": "error_spike",
        "expected_behavior": (
            "Error rate on /api/error increased from ~5% to ~40% of all traffic. "
            "This should be visible as a sharp spike in the error rate panel and "
            "in the error category breakdown (SYSTEM_ERROR). The anomaly window "
            "lasts exactly 2 minutes."
        )
    }

    with open("ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)
    print("")
    print("  ground_truth.json written!")
    print("  Anomaly window: " + anomaly_start_iso + " -> " + anomaly_end_iso)


if __name__ == "__main__":
    main()
