import re
from typing import List, Optional
from .base import Finding

class HardcodedInterval:
    def check(self, query: str) -> List[Finding]:
        # Detect rate/irate/increase calls with hardcoded time durations like [5m], [1h], [30s]
        # instead of [$__rate_interval] or [$__interval].
        
        # We look for rate|irate|increase followed by ( and eventually [5m] or similar
        # Pattern: (rate|irate|increase)\s*\(.*\[\d+[smh]\]
        
        matches = re.finditer(r'(rate|irate|increase)\s*\([^)]*\[(\d+[smh])\]', query)
        
        findings = []
        for match in matches:
            func_name = match.group(1)
            duration = match.group(2)
            
            # If the expression already uses template variables, skip it
            if "$__rate_interval" in query or "$__interval" in query:
                continue
                
            findings.append(Finding(
                rule_id="Q7",
                severity="Medium",
                title="Hardcoded interval in rate function",
                why=f"{func_name}() uses a hardcoded duration [{duration}] instead of $__rate_interval or $__interval. This breaks when the dashboard time range or scrape interval changes.",
                fix=f"Replace the hardcoded duration with $__rate_interval, e.g. {func_name}(metric[$__rate_interval]).",
                impact="Ensures correct per-point calculations regardless of time range or scrape config",
                confidence=0.9
            ))
        return findings
