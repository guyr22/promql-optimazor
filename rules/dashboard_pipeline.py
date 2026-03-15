from typing import List
from .base import Finding
from .d1_too_many_panels import TooManyPanels
from .d5_refresh_too_frequent import RefreshTooFrequent
from .d6_range_too_wide import RangeTooWide

def run_dashboard_pipeline(dashboard: dict) -> List[Finding]:
    """
    Runs the dashboard-level rule pipeline in order: D1 -> D5 -> D6.
    """
    rules = [
        TooManyPanels(),
        RefreshTooFrequent(),
        RangeTooWide()
    ]
    
    all_findings = []
    for rule in rules:
        all_findings.extend(rule.check(dashboard))
        
    return all_findings
