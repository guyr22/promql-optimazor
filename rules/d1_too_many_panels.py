from typing import List, Optional
from .base import Finding, get_visible_panels

class TooManyPanels:
    def __init__(self, threshold: int = 25):
        self.threshold = threshold

    def check(self, dashboard: dict) -> List[Finding]:
        visible = get_visible_panels(dashboard)
        count = len(visible)
        
        if count <= self.threshold:
            return []

        return [
            Finding(
                rule_id="D1",
                severity="High",
                title="Too many visible panels",
                why=f"Dashboard has {count} visible panels (threshold: {self.threshold}). Each panel fires queries on load, causing slow initial render and high backend load.",
                fix="Group related panels into collapsed rows, or split the dashboard into multiple focused dashboards.",
                impact=f"Reducing from {count} to ≤{self.threshold} panels cuts initial query load proportionally",
                confidence=1.0,
            )
        ]
