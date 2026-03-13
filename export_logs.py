#!/usr/bin/env python3
"""
# ============================================================================
# [LAB WORK 3] - ML Anomaly Detection
# This script extracts structured JSON logs from the Laravel standard storage
# (storage/logs/aiops.log) and validates that the >=1500 logs requirement is met.
# ============================================================================
"""

import json
import sys
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "storage", "logs", "aiops.log")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "logs.json")

REQUIRED_KEYS = [
    "timestamp", "trace_id", "method", "path", "client_ip", "user_agent",
    "query", "payload_size_bytes", "response_size_bytes", "route_name",
    "severity", "build_version", "host", "status_code", "error_category",
    "latency_ms"
]


def main():
    if not os.path.exists(LOG_FILE):
        print(f"ERROR: Log file not found at {LOG_FILE}")
        print("Run the traffic generator first!")
        sys.exit(1)

    entries = []
    errors = 0
    schema_issues = 0

    with open(LOG_FILE, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"  WARNING: Line {line_num} is not valid JSON, skipping")
                schema_issues += 1
                continue

            # Validate required keys
            missing = [k for k in REQUIRED_KEYS if k not in record]
            if missing:
                print(f"  WARNING: Line {line_num} missing keys: {missing}")
                schema_issues += 1
                # Add missing keys as null for stable schema
                for k in missing:
                    record[k] = None

            entries.append(record)

            # Count errors
            if record.get("error_category") not in (None, "NONE"):
                errors += 1

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"\n{'='*50}")
    print(f"  Log Export Results")
    print(f"  Total entries: {len(entries)}")
    print(f"  Error entries: {errors}")
    print(f"  Schema issues: {schema_issues}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"{'='*50}")

    # Validate requirements
    ok = True
    if len(entries) < 1500:
        print(f"\n  FAIL: Need ≥1500 entries, got {len(entries)}")
        ok = False
    else:
        print(f"\n  PASS: ≥1500 entries ({len(entries)})")

    if errors < 100:
        print(f"  FAIL: Need ≥100 error logs, got {errors}")
        ok = False
    else:
        print(f"  PASS: ≥100 error logs ({errors})")

    if ok:
        print("\n  All checks passed!")
    else:
        print("\n  Some checks failed. Run more traffic to generate more logs.")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
