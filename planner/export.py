from __future__ import annotations

import csv
import io
import json


def snapshot_json(snapshot: dict) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True)


def sessions_csv(snapshot: dict) -> str:
    rows = snapshot.get("sessions", [])
    fields = ["id", "session_date", "topic_id", "planned_minutes", "actual_minutes", "session_type", "performance_score", "completed"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in fields})
    return out.getvalue()
