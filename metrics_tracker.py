"""
MetricsTracker — records MTTD / MTTR per incident and exports to CSV.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)
METRICS_FILE = "metrics.csv"


class MetricsTracker:
    def __init__(self):
        self._timings: dict = {}
        if not Path(METRICS_FILE).exists():
            with open(METRICS_FILE, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["incident_id", "detected_at", "resolved_at",
                     "mttd_seconds", "mttr_seconds", "auto_remediated"])

    def record_detection(self, incident_id: str):
        self._timings[incident_id] = {"detected_at": datetime.utcnow()}

    def record_resolution(self, incident_id: str, auto_remediated: bool = False):
        if incident_id not in self._timings:
            return
        resolved_at = datetime.utcnow()
        detected_at = self._timings[incident_id]["detected_at"]
        mttr = (resolved_at - detected_at).total_seconds()

        with open(METRICS_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                incident_id,
                detected_at.isoformat(),
                resolved_at.isoformat(),
                0,       # MTTD tracked externally
                round(mttr, 2),
                auto_remediated,
            ])
        log.info(f"MTTR for {incident_id}: {mttr:.0f}s | auto={auto_remediated}")
        del self._timings[incident_id]
