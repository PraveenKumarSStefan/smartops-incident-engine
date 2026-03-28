"""
IncidentStore — SQLite-backed incident history tracker.
"""

import sqlite3
import uuid
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
DB_PATH = "incidents.db"


class IncidentStore:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id          TEXT PRIMARY KEY,
                    service     TEXT,
                    severity    TEXT,
                    source      TEXT,
                    error_rate  REAL,
                    status      TEXT DEFAULT 'open',
                    method      TEXT,
                    created_at  TEXT,
                    resolved_at TEXT
                )
            """)

    def create(self, anomaly: dict, severity: str) -> str:
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO incidents (id, service, severity, source, error_rate, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (incident_id, anomaly.get("service"), severity,
                 anomaly.get("source"), anomaly.get("error_rate", 0),
                 datetime.utcnow().isoformat())
            )
        return incident_id

    def resolve(self, incident_id: str, method: str = "manual"):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE incidents SET status='resolved', method=?, resolved_at=? WHERE id=?",
                (method, datetime.utcnow().isoformat(), incident_id)
            )

    def is_duplicate(self, anomaly: dict, window_minutes: int = 15) -> bool:
        cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT id FROM incidents WHERE service=? AND status='open' AND created_at > ?",
                (anomaly.get("service"), cutoff)
            ).fetchone()
        return row is not None
