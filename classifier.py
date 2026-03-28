"""
SeverityClassifier — classifies anomalies into P1, P2, P3 based on rules.
"""

import logging
log = logging.getLogger(__name__)


class SeverityClassifier:
    def __init__(self, thresholds: dict):
        self.p1_rate = thresholds.get("p1_error_rate", 0.10)
        self.p2_rate = thresholds.get("p2_error_rate", 0.05)
        self.p3_rate = thresholds.get("p3_error_rate", 0.01)

    def classify(self, error_rate: float, affected_services: int = 1,
                 is_payment_path: bool = False) -> str | None:
        """
        Returns 'P1', 'P2', 'P3', or None if below threshold.

        Rules (in priority order):
        P1 — payment path affected OR error_rate > 10%
        P2 — error_rate > 5% OR 3+ services affected
        P3 — error_rate > 1%
        """
        if is_payment_path or error_rate >= self.p1_rate:
            log.info(f"Classified P1 | rate={error_rate:.2%} | payment={is_payment_path}")
            return "P1"

        if error_rate >= self.p2_rate or affected_services >= 3:
            log.info(f"Classified P2 | rate={error_rate:.2%} | services={affected_services}")
            return "P2"

        if error_rate >= self.p3_rate:
            log.info(f"Classified P3 | rate={error_rate:.2%}")
            return "P3"

        return None
