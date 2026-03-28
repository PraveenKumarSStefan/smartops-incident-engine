"""
SlackNotifier — sends structured war-room alerts and resolution updates to Slack.
"""

import requests
import logging
from datetime import datetime

log = logging.getLogger(__name__)

SEVERITY_EMOJI = {"P1": "🔴", "P2": "🟠", "P3": "🟡"}
SEVERITY_COLOR = {"P1": "#FF0000", "P2": "#FF8C00", "P3": "#FFD700"}


class SlackNotifier:
    def __init__(self, config: dict):
        self.webhook_url = config["webhook_url"]
        self.channel     = config.get("war_room_channel", "#production-incidents")

    def send_alert(self, incident_id: str, severity: str, anomaly: dict):
        emoji = SEVERITY_EMOJI.get(severity, "⚠️")
        color = SEVERITY_COLOR.get(severity, "#808080")
        ts    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        payload = {
            "channel": self.channel,
            "text"   : f"{emoji} *[{severity}] Production Incident #{incident_id} Detected*",
            "attachments": [{
                "color" : color,
                "fields": [
                    {"title": "Incident ID",      "value": incident_id,                          "short": True},
                    {"title": "Severity",          "value": severity,                             "short": True},
                    {"title": "Affected Service",  "value": anomaly.get("service", "unknown"),   "short": True},
                    {"title": "Error Rate",        "value": f"{anomaly.get('error_rate',0):.2%}", "short": True},
                    {"title": "Source",            "value": anomaly.get("source", "unknown"),    "short": True},
                    {"title": "Payment Path",      "value": str(anomaly.get("is_payment_path", False)), "short": True},
                    {"title": "Detected At",       "value": ts,                                  "short": False},
                    {"title": "Action",
                     "value": "Auto-remediation triggered" if severity in ("P2","P3") else "⚠️ Manual war-room required",
                     "short": False},
                ],
                "footer": "SmartOps Incident Engine",
                "ts"    : int(datetime.utcnow().timestamp()),
            }]
        }
        self._post(payload)

    def send_resolution(self, incident_id: str, severity: str, anomaly: dict):
        payload = {
            "channel": self.channel,
            "text"   : f"✅ *[{severity}] Incident #{incident_id} Auto-Resolved*",
            "attachments": [{
                "color" : "#36a64f",
                "fields": [
                    {"title": "Service",    "value": anomaly.get("service", "unknown"), "short": True},
                    {"title": "Resolution", "value": "Ansible runbook executed",        "short": True},
                ],
                "footer": "SmartOps Incident Engine",
            }]
        }
        self._post(payload)

    def _post(self, payload: dict):
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            log.error(f"Slack notification failed: {e}")
