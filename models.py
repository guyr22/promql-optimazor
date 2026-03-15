from pydantic import BaseModel
from typing import List, Optional


class DashboardOptimizeRequest(BaseModel):
    dashboard_uid: str
    panels_count: Optional[int] = None
    time_range: str = "1h"

class OptimizationResult(BaseModel):
    panel_title: str
    original_query: str
    original_latency: Optional[str] = None
    original_cardinality: Optional[int] = None
    optimized_query: Optional[str] = None
    optimized_latency: Optional[str] = None
    optimized_cardinality: Optional[int] = None
    explanation: Optional[str] = None
    grade: Optional[int] = None
    error: Optional[str] = None
    recommendation: Optional[List[str]] = None

class DashboardOptimizeResponse(BaseModel):
    dashboard_title: str
    dashboard_uid: str
    optimizations: List[OptimizationResult]
    dashboard_recommendations: Optional[List[str]] = None

