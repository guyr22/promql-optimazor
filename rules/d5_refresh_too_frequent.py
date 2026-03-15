from datetime import timedelta
from typing import List, Optional
from .base import Finding, parse_grafana_duration

class RefreshTooFrequent:
    def __init__(self, min_refresh: timedelta = timedelta(seconds=30)):
        self.min_refresh = min_refresh

    def check(self, dashboard: dict) -> List[Finding]:
        raw = dashboard.get("refresh", "")
        if not raw:
            return []

        d = parse_grafana_duration(raw)
        if not d:
            return []

        if d >= self.min_refresh:
            return []

        min_s = int(self.min_refresh.total_seconds())
        reduction = (1.0 - d.total_seconds() / self.min_refresh.total_seconds()) * 100

        return [
            Finding(
                rule_id="D5",
                severity="Medium",
                title="Auto-refresh interval too frequent",
                why=f"Dashboard refresh is set to {raw}. Intervals below {min_s}s cause continuous backend query load, especially when many users have the dashboard open.",
                fix=f"Set the dashboard refresh interval to {min_s}s or longer.",
                impact=f"Changing refresh from {raw} to {min_s}s reduces query rate by {reduction:.0f}%",
                confidence=1.0,
            )
        ]
