import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from query_optimizer import PromQLOptimizerAgent

load_dotenv()

app = FastAPI(
    title="PromQL Optimizer API",
    description="API to optimize PromQL queries from a Grafana dashboard",
    version="1.0.0"
)

# Configuration for Grafana
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")

# Initialize the optimizer agent. Will look for RAG-CONTEXT.txt in the same directory.
try:
    optimizer_agent = PromQLOptimizerAgent()
except Exception as e:
    print(f"Warning: Failed to initialize PromQLOptimizerAgent: {e}")
    optimizer_agent = None


class DashboardOptimizeRequest(BaseModel):
    dashboard_uid: str

class OptimizationResult(BaseModel):
    panel_title: str
    original_query: str
    optimized_query: Optional[str] = None
    explanation: Optional[str] = None
    grade: Optional[int] = None
    error: Optional[str] = None

class DashboardOptimizeResponse(BaseModel):
    dashboard_title: str
    dashboard_uid: str
    optimizations: List[OptimizationResult]


def fetch_grafana_dashboard(uid: str) -> Dict[str, Any]:
    """Fetches the dashboard JSON payload from Grafana HTTP API."""
    if not GRAFANA_API_KEY:
        raise ValueError("GRAFANA_API_KEY environment variable is not set")
        
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{GRAFANA_URL.rstrip('/')}/api/dashboards/uid/{uid}"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch dashboard: {response.text}")
    
    return response.json()


def extract_variables(dashboard_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts dashboard variables and their current values."""
    variables = {}
    dashboard = dashboard_json.get("dashboard", {})
    templating = dashboard.get("templating", {}).get("list", [])
    
    for var in templating:
        name = var.get("name")
        current_value = var.get("current", {}).get("value")
        if name:
            variables[name] = {
                "value": current_value,
                "is_multi": var.get("multi", False),
                "include_all": var.get("includeAll", False)
            }
            
    return variables


import time
import re

# Configuration for Prometheus
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

def evaluate_promql(query: str, variables: Dict[str, Any]) -> tuple[str, int]:
    """
    Substitutes Grafana variables and evaluates the query against Prometheus 
    to get actual latency and cardinality.
    """
    substituted_query = query
    # Very basic variable substitution for $var, ${var}, or [[var]]
    for var_name, var_value in variables.items():
        if isinstance(var_value, list):
            val_str = "|".join(str(v) for v in var_value)
        elif isinstance(var_value, dict) and "value" in var_value:
             # handle complex grafana variable objects if passed
             val_str = str(var_value["value"])
        else:
            val_str = str(var_value)
            
        # Replace occurrences
        safe_val = val_str.replace("$", "$$") # escape for regex replacement if needed, though simple replace is easier
        substituted_query = substituted_query.replace(f"${{{var_name}}}", val_str)
        substituted_query = substituted_query.replace(f"${var_name}", val_str)
        substituted_query = substituted_query.replace(f"[[{var_name}]]", val_str)

    try:
        url = f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query"
        start_time = time.time()
        response = requests.get(url, params={"query": substituted_query}, timeout=10)
        end_time = time.time()
        
        latency_secs = end_time - start_time
        latency_str = f"{latency_secs:.3f}s"
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            results = data.get("result", [])
            cardinality = len(results)
        else:
            cardinality = 0
            latency_str = f"Error {response.status_code}"
            
    except Exception as e:
        latency_str = f"Failed to execute: {str(e)}"
        cardinality = 0

    return latency_str, cardinality

def process_panel(panel: Dict[str, Any], variables: Dict[str, Any], optimizations: List[OptimizationResult]):
    """Extracts queries from a single panel and sends them to the optimizer."""
    panel_title = panel.get("title", "Untitled Panel")
    targets = panel.get("targets", [])
    
    for target in targets:
        # Typically the PromQL query is in target['expr']
        expr = target.get("expr")
        if not expr:
            continue
            
        # Execute against Prometheus to get real performance metrics
        latency, cardinality = evaluate_promql(expr, variables)
        
        if optimizer_agent is None:
            optimizations.append(OptimizationResult(
                panel_title=panel_title,
                original_query=expr,
                error="Optimizer agent not initialized. Check server logs."
            ))
        else:
            try:
                result_dict = optimizer_agent.optimize_query(
                    raw_query=expr,
                    variable_context=variables,
                    latency=latency,
                    cardinality=cardinality
                )
                
                if result_dict:
                    explanation_val = result_dict.get('explanation')
                    if isinstance(explanation_val, list):
                        explanation_val = " ".join(str(x) for x in explanation_val)
                        
                    optimizations.append(OptimizationResult(
                        panel_title=panel_title,
                        original_query=expr,
                        optimized_query=result_dict.get('optimized_query'),
                        explanation=explanation_val,
                        grade=result_dict.get('grade')
                    ))
                else:
                    optimizations.append(OptimizationResult(
                        panel_title=panel_title,
                        original_query=expr,
                        error="Optimizer returned no result."
                    ))
                    
            except Exception as e:
                optimizations.append(OptimizationResult(
                    panel_title=panel_title,
                    original_query=expr,
                    error=f"Error during optimization: {str(e)}"
                ))


@app.post("/optimize-dashboard", response_model=DashboardOptimizeResponse)
async def optimize_dashboard(request: DashboardOptimizeRequest):
    """
    Receives a Grafana dashboard UID, fetches its definition, parses out all PromQL queries,
    and runs them through the optimizer agent.
    """
    try:
        dashboard_data = fetch_grafana_dashboard(request.dashboard_uid)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    dashboard = dashboard_data.get("dashboard", {})
    dashboard_title = dashboard.get("title", "Unknown Dashboard")
    
    variables = extract_variables(dashboard_data)
    optimizations = []
    
    panels = dashboard.get("panels", [])
    for panel in panels:
        if panel.get("type") == "row":
            # Rows contain nested panels
            sub_panels = panel.get("panels", [])
            for sub_panel in sub_panels:
                process_panel(sub_panel, variables, optimizations)
        else:
            process_panel(panel, variables, optimizations)
            
    return DashboardOptimizeResponse(
        dashboard_title=dashboard_title,
        dashboard_uid=request.dashboard_uid,
        optimizations=optimizations
    )

# For running locally via Python:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
