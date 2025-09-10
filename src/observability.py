# src/observability.py
import json
import os
from datetime import datetime
ARTIFACTS = "artifacts"
os.makedirs(ARTIFACTS, exist_ok=True)
TRACE_FILE = os.path.join(ARTIFACTS, "sample_trace.json")

def log_trace(step: str, data: dict):
    entry = {"time": datetime.utcnow().isoformat(), "step": step, "data": data}
    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def export_run_summary(summary: dict):
    summary_file = os.path.join(ARTIFACTS, "run_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
