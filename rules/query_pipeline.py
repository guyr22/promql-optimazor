from typing import List
from .base import Finding
from .q2_unbounded_regex import UnboundedRegex
from .q7_hardcoded_interval import HardcodedInterval
from .q10_incorrect_aggregation import IncorrectAggregation
from .q11_rate_on_gauge import RateOnGauge

def run_query_pipeline(query: str) -> List[Finding]:
    """
    Runs the query-level rule pipeline in order: Q2 -> Q11 -> Q10 -> Q7.
    """
    rules = [
        UnboundedRegex(),
        RateOnGauge(),
        IncorrectAggregation(),
        HardcodedInterval()
    ]
    
    all_findings = []
    for rule in rules:
        all_findings.extend(rule.check(query))
        
    return all_findings
