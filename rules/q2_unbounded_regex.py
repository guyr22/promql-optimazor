import re
from typing import List, Optional
from .base import Finding

class UnboundedRegex:
    def check(self, query: str) -> List[Finding]:
        # Regex to find label matchers like label=~"regex" or label!~"regex"
        # Operator order is =~ or !~ in PromQL
        matchers = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*([!=]~)\s*"([^"]+)"', query)
        
        findings = []
        for name, op, value in matchers:
            if name == "__name__":
                continue
                
            reason = self._unbounded_regex_reason(value)
            if reason:
                findings.append(Finding(
                    rule_id="Q2",
                    severity="High",
                    title="Unbounded regex matcher",
                    why=f"Label '{name}' uses regex {op}\"{value}\" — {reason}. This can force a full scan of all label values.",
                    fix=f"Rewrite the regex for {name} to be more specific, e.g. use a prefix match or equality.",
                    impact="Reduces label value scanning and regex evaluation overhead significantly",
                    confidence=0.85
                ))
        return findings

    def _unbounded_regex_reason(self, value: str) -> Optional[str]:
        # Strip internal spaces to be robust against " . +" or " .+"
        val = value.replace(" ", "")
        
        if val == ".+":
            return "pattern .+ matches every non-empty label value"
        if val.startswith(".*"):
            return "leading .* causes a full scan of all label values"
        
        # Check for .* in the middle (not at start or end)
        trimmed = val
        if trimmed.endswith(".*"):
            trimmed = trimmed[:-2]
            
        if ".*" in trimmed[1:]: # idx > 0
            return "mid-pattern .* causes expensive backtracking"
            
        return None
