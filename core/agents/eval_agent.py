# agents/EvalAgent.py
import time

class EvalAgent:
    def evaluate(self, output):
        """
        Evaluates pipeline output and returns metrics.
        """
        # Placeholder metrics
        metrics = {
            "processed_samples": len(output) if hasattr(output, '__len__') else None,
            "evaluation_time": time.time()
        }
        return metrics

# memory/store.py
import json, os

DB_PATH = "memory/db.json"

def save_run(metadata):
    if os.path.exists(DB_PATH):
        data = json.load(open(DB_PATH))
    else:
        data = []
    data.append(metadata)
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)
