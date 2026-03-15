import re
from typing import List, Optional
from .base import Finding

class IncorrectAggregation:
    def check(self, query: str) -> List[Finding]:
        # Detect patterns like rate(sum(...)), irate(avg(...)), increase(count(...))
        # This is mathematically wrong because rate() expects monotonically increasing counter values.
        
        pattern = r'(rate|irate|increase)\s*\(\s*(sum|avg|min|max|count)\s*\('
        matches = re.finditer(pattern, query)
        
        findings = []
        for match in matches:
            outer_func = match.group(1)
            inner_func = match.group(2)
            
            findings.append(Finding(
                rule_id="Q10",
                severity="Medium",
                title="Incorrect aggregation order",
                why=f"Expression applies {outer_func}() over an aggregation ({inner_func}). Rate-like functions expect raw counter values, but aggregation output is not a monotonic counter — results will be mathematically incorrect.",
                fix=f"Reverse the order: apply {outer_func}() first on the raw metric, then aggregate. E.g. {inner_func}({outer_func}(metric[5m])) instead of {outer_func}({inner_func}(metric)[5m]).",
                impact="Produces mathematically correct results and often reduces series scanned",
                confidence=0.85
            ))
        return findings
