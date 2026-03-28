"""
AnomalyDetector — polls Splunk REST API and Prometheus for anomalies.
"""

import requests
import logging
from typing import List, Dict

log = logging.getLogger(__name__)

PAYMENT_SERVICES = {"payment-gateway", "checkout", "order-service", "transaction-api"}


class AnomalyDetector:
    def __init__(self, config: dict):
        self.splunk_cfg     = config["splunk"]
        self.prometheus_cfg = config["prometheus"]

    def poll(self) -> List[Dict]:
        anomalies = []
        anomalies.extend(self._poll_splunk())
        anomalies.extend(self._poll_prometheus())
        return anomalies

    # ── SPLUNK ────────────────────────────────────────────────────────────────
    def _poll_splunk(self) -> List[Dict]:
        results = []
        try:
            url = f"{self.splunk_cfg['host']}/services/search/jobs/export"
            headers = {"Authorization": f"Bearer {self.splunk_cfg['token']}"}
            payload = {
                "search": self.splunk_cfg["search_query"],
                "output_mode": "json",
                "count": 100,
            }
            resp = requests.post(url, headers=headers, data=payload, verify=False, timeout=15)
            resp.raise_for_status()

            for line in resp.text.strip().splitlines():
                try:
                    import json
                    record = json.loads(line)
                    result = record.get("result", {})
                    service    = result.get("service", "unknown")
                    error_count = int(result.get("count", 0))
                    total_count = int(result.get("total", 1))
                    error_rate  = error_count / total_count if total_count else 0

                    if error_rate > 0.01:
                        results.append({
                            "source"          : "splunk",
                            "service"         : service,
                            "error_rate"      : error_rate,
                            "error_count"     : error_count,
                            "is_payment_path" : service in PAYMENT_SERVICES,
                        })
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"Splunk poll failed: {e}")
        return results

    # ── PROMETHEUS ────────────────────────────────────────────────────────────
    def _poll_prometheus(self) -> List[Dict]:
        results = []
        try:
            url  = f"{self.prometheus_cfg['host']}/api/v1/alerts"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            alerts = resp.json().get("data", {}).get("alerts", [])

            for alert in alerts:
                if alert.get("state") != "firing":
                    continue
                labels  = alert.get("labels", {})
                service = labels.get("job", labels.get("service", "unknown"))
                severity_label = labels.get("severity", "warning")
                error_rate = 0.06 if severity_label == "critical" else 0.02

                results.append({
                    "source"          : "prometheus",
                    "service"         : service,
                    "error_rate"      : error_rate,
                    "alert_name"      : labels.get("alertname", ""),
                    "is_payment_path" : service in PAYMENT_SERVICES,
                })
        except Exception as e:
            log.warning(f"Prometheus poll failed: {e}")
        return results
