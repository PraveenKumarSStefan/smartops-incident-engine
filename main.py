"""
SmartOps — AI-Powered Incident Detection & Auto-Remediation Engine
Entry point: starts the polling loop and orchestrates the full pipeline.
Author: Praveenkumar S
"""

import time
import logging
from src.detector import AnomalyDetector
from src.classifier import SeverityClassifier
from src.remediation import RemediationEngine
from src.notifier import SlackNotifier
from src.metrics_tracker import MetricsTracker
from src.incident_store import IncidentStore
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("smartops.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def run():
    log.info("🚀 SmartOps Engine starting...")
    cfg = load_config()

    detector    = AnomalyDetector(cfg)
    classifier  = SeverityClassifier(cfg["thresholds"])
    remediation = RemediationEngine(cfg["ansible"])
    notifier    = SlackNotifier(cfg["slack"])
    tracker     = MetricsTracker()
    store       = IncidentStore()

    log.info("✅ All components initialised. Entering polling loop.")

    while True:
        try:
            anomalies = detector.poll()

            for anomaly in anomalies:
                # Skip if already active & within dedup window
                if store.is_duplicate(anomaly):
                    log.debug(f"Suppressing duplicate: {anomaly['service']}")
                    continue

                # Classify severity
                severity = classifier.classify(
                    error_rate        = anomaly["error_rate"],
                    affected_services = anomaly.get("affected_services", 1),
                    is_payment_path   = anomaly.get("is_payment_path", False),
                )
                if not severity:
                    continue

                # Open incident
                incident_id = store.create(anomaly, severity)
                tracker.record_detection(incident_id)
                log.info(f"🔴 [{severity}] Incident #{incident_id} — {anomaly['service']}")

                # Notify war room
                notifier.send_alert(incident_id, severity, anomaly)

                # Attempt auto-remediation for P2/P3
                if severity in ("P2", "P3"):
                    success = remediation.run(anomaly)
                    tracker.record_resolution(incident_id, auto_remediated=success)
                    if success:
                        store.resolve(incident_id, method="auto-remediation")
                        notifier.send_resolution(incident_id, severity, anomaly)
                        log.info(f"✅ Incident #{incident_id} auto-remediated.")
                    else:
                        log.warning(f"⚠️ Auto-remediation failed for #{incident_id} — engineer notified.")
                else:
                    log.info(f"🚨 P1 incident #{incident_id} — manual war room required.")

        except Exception as e:
            log.error(f"Engine error: {e}", exc_info=True)

        time.sleep(cfg["splunk"].get("poll_interval_seconds", 60))


if __name__ == "__main__":
    run()
