"""
RemediationEngine — selects and triggers the appropriate Ansible runbook.
"""

import subprocess
import logging
import os

log = logging.getLogger(__name__)

# Map alert_name / service patterns → runbook
RUNBOOK_MAP = {
    "high_memory"     : "flush_cache.yml",
    "disk_full"       : "disk_cleanup.yml",
    "service_down"    : "restart_service.yml",
    "connection_pool" : "restart_service.yml",
    "default"         : "restart_service.yml",
}


class RemediationEngine:
    def __init__(self, config: dict):
        self.playbook_dir = config.get("playbook_dir", "./ansible")
        self.inventory    = config.get("inventory", "./ansible/inventory.ini")

    def run(self, anomaly: dict) -> bool:
        alert_name = anomaly.get("alert_name", "default").lower()
        runbook    = self._select_runbook(alert_name)
        playbook   = os.path.join(self.playbook_dir, runbook)

        if not os.path.exists(playbook):
            log.warning(f"Runbook not found: {playbook}")
            return False

        service = anomaly.get("service", "unknown")
        log.info(f"Running runbook: {runbook} for service: {service}")

        try:
            result = subprocess.run(
                ["ansible-playbook", playbook,
                 "-i", self.inventory,
                 "--extra-vars", f"target_service={service}"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                log.info(f"Runbook succeeded: {runbook}")
                return True
            else:
                log.error(f"Runbook failed: {result.stderr[:500]}")
                return False
        except subprocess.TimeoutExpired:
            log.error(f"Runbook timed out: {runbook}")
            return False
        except FileNotFoundError:
            log.error("ansible-playbook not found in PATH")
            return False

    def _select_runbook(self, alert_name: str) -> str:
        for key, runbook in RUNBOOK_MAP.items():
            if key in alert_name:
                return runbook
        return RUNBOOK_MAP["default"]
