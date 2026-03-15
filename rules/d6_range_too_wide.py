from datetime import timedelta
from typing import List, Optional
from .base import Finding, parse_grafana_duration

class RangeTooWide:
    def __init__(self, max_range: timedelta = timedelta(hours=24)):
        self.max_range = max_range

    def check(self, dashboard: dict) -> List[Finding]:
        # Grafana dashboard time is in dashboard['time']['from']
        time_config = dashboard.get("time", {})
        from_str = time_config.get("from", "")
        
        if not from_str.startswith("now-"):
            return []
            
        duration_str = from_str[4:]
        d = parse_grafana_duration(duration_str)
        if not d:
            return []

        if d <= self.max_range:
            return []

        max_h = int(self.max_range.total_seconds() / 3600)
        return [
            Finding(
                rule_id="D6",
                severity="Medium",
                title="Default time range too wide",
                why=f"Dashboard default time range is '{from_str}' ({d}). Ranges wider than {max_h}h pull large data volumes per query, increasing response times and memory usage.",
                fix=f"Set the default time range to {max_h}h or less (e.g., \"now-6h\" or \"now-1h\").",
                impact=f"Narrowing from {d} to {max_h}h reduces data scanned per query proportionally",
                confidence=1.0,
            )
        ]
