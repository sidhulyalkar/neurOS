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