import re
from dataclasses import dataclass
from typing import List, Optional, Union
from datetime import timedelta

@dataclass
class Finding:
    rule_id: str
    severity: str
    title: str
    why: str
    fix: str
    impact: str
    confidence: float = 1.0

def get_visible_panels(dashboard: dict) -> List[dict]:
    """
    Extracts visible panels from a Grafana dashboard JSON.
    Visible panels are top-level panels or panels within uncollapsed rows.
    """
    panels = dashboard.get("panels", [])
    visible = []
    
    for panel in panels:
        if panel.get("type") == "row":
            # If the row is NOT collapsed, its sub-panels are visible
            if not panel.get("collapsed", False):
                visible.extend(panel.get("panels", []))
        else:
            visible.append(panel)
            
    return visible

def parse_grafana_duration(s: str) -> Optional[timedelta]:
    """
    Parses Grafana-style duration strings such as "5s", "1m", "1h", "7d", "1w", "ms".
    """
    if not s:
        return None
        
    match = re.match(r"^(\d+)(ms|[smhdwy])$", s)
    if not match:
        return None
        
    n = int(match.group(1))
    suffix = match.group(2)
    
    if suffix == "ms":
        return timedelta(milliseconds=n)
    elif suffix == "s":
        return timedelta(seconds=n)
    elif suffix == "m":
        return timedelta(minutes=n)
    elif suffix == "h":
        return timedelta(hours=n)
    elif suffix == "d":
        return timedelta(days=n)
    elif suffix == "w":
        return timedelta(weeks=n)
    elif suffix == "y":
        return timedelta(days=n*365) # Approximation
        
    return None
