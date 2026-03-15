import re
from typing import List, Optional
from .base import Finding

class RateOnGauge:
    KNOWN_GAUGE_PREFIXES = [
        "go_goroutines",
        "go_threads",
        "go_memstats_",
        "go_info",
        "process_resident_memory_bytes",
        "process_virtual_memory_bytes",
        "process_open_fds",
        "process_max_fds",
        "node_memory_",
        "node_filesystem_",
        "node_load",
        "node_time_seconds",
        "node_boot_time_seconds",
        "prometheus_tsdb_head_series",
        "prometheus_tsdb_head_chunks",
        "up"
    ]

    def check(self, query: str) -> List[Finding]:
        # Detect rate() or irate() applied to gauge-type metrics.
        # Pattern: (rate|irate)\s*\(([a-zA-Z_:][a-zA-Z0-9_:]*)
        
        matches = re.finditer(r'(rate|irate)\s*\(\s*([a-zA-Z_:][a-zA-Z0-9_:]*)', query)
        
        findings = []
        for match in matches:
            func_name = match.group(1)
            metric_name = match.group(2)
            
            if self._is_likely_gauge(metric_name):
                findings.append(Finding(
                    rule_id="Q11",
                    severity="Medium",
                    title="rate()/irate() on gauge metric",
                    why=f"{func_name}() is applied to '{metric_name}', which appears to be a gauge metric. rate/irate compute per-second change and only produce meaningful results on counters (_total, _count, _bucket).",
                    fix=f"Use the metric directly ({metric_name}) or use delta() / deriv() instead of {func_name}() for gauge metrics.",
                    impact="Correct function choice produces accurate visualizations instead of mostly-zero noise",
                    confidence=0.6
                ))
        return findings

    def _is_likely_gauge(self, name: str) -> bool:
        # Counters end in _total, _count, _sum, _bucket — these are NOT gauges
        if name.endswith(("_total", "_count", "_sum", "_bucket")):
            return False
            
        for prefix in self.KNOWN_GAUGE_PREFIXES:
            if name.startswith(prefix):
                return True
        return False
