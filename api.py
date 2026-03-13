import os
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any, Optional, Generator
from dotenv import load_dotenv

from optimizers import get_optimizer
from models import DashboardOptimizeRequest, OptimizationResult, DashboardOptimizeResponse
from grafana_client import (
    fetch_grafana_dashboard,
    extract_variables,
    get_prometheus_url,
    clear_datasource_cache,
)
from prometheus_client import evaluate_promql

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("promql-optimizer")

app = FastAPI(
    title="PromQL Optimizer API",
    description="API to optimize PromQL queries from a Grafana dashboard",
    version="1.0.0"
)

# Initialize the optimizer agent using the factory.
try:
    optimizer_type = os.getenv("OPTIMIZER_TYPE", "gemini")
    optimizer_agent = get_optimizer(optimizer_type)
    logger.info(f"Successfully initialized {optimizer_agent.__class__.__name__}")
except Exception as e:
    logger.error(f"Failed to initialize optimizer agent: {e}")
    optimizer_agent = None


def process_panel(panel: Dict[str, Any], variables: Dict[str, Any], optimizations: List[OptimizationResult], time_range: str = "1h"):
    """Extracts queries from a single panel and sends them to the optimizer."""
    panel_title = panel.get("title", "Untitled Panel")
    targets = panel.get("targets", [])
    
    for target in targets:
        # Typically the PromQL query is in target['expr']
        expr = target.get("expr")
        if not expr:
            continue
        logger.info(f"Processing query from panel '{panel_title}': {expr}")
        
        # Resolve the datasource for this target
        datasource_ref = target.get("datasource")
        prometheus_url = None
        
        if datasource_ref:
            resolved_url = get_prometheus_url(datasource_ref, variables)
            if resolved_url == "NOT_PROMETHEUS":
                logger.info(f"Skipping non-Prometheus query in panel '{panel_title}'")
                optimizations.append(OptimizationResult(
                    panel_title=panel_title,
                    original_query=expr,
                    error="Skipped: datasource is not Prometheus."
                ))
                continue
            prometheus_url = resolved_url  # May be None (fallback) or a direct URL
        
        # Execute against Prometheus to get real performance metrics
        latency, cardinality = evaluate_promql(expr, variables, time_range, prometheus_url=prometheus_url)
        
        if optimizer_agent is None:
            logger.error("Optimizer agent is not initialized.")
            optimizations.append(OptimizationResult(
                panel_title=panel_title,
                original_query=expr,
                original_latency=latency,
                original_cardinality=cardinality,
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
                    
                    optimized_query = result_dict.get('optimized_query')
                    opt_latency = None
                    opt_cardinality = None
                    
                    # Re-evaluate both queries in parallel for a fair comparison
                    if optimized_query and optimized_query != expr:
                        logger.info(f"Evaluating original and optimized queries in parallel for panel '{panel_title}'")
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            original_future = executor.submit(
                                evaluate_promql, expr, variables, time_range, prometheus_url
                            )
                            optimized_future = executor.submit(
                                evaluate_promql, optimized_query, variables, time_range, prometheus_url
                            )
                            latency, cardinality = original_future.result()
                            opt_latency, opt_cardinality = optimized_future.result()
                        
                    optimizations.append(OptimizationResult(
                        panel_title=panel_title,
                        original_query=expr,
                        original_latency=latency,
                        original_cardinality=cardinality,
                        optimized_query=optimized_query,
                        optimized_latency=opt_latency,
                        optimized_cardinality=opt_cardinality,
                        explanation=explanation_val,
                        grade=result_dict.get('grade')
                    ))
                    logger.info(f"Successfully generated optimization for query in '{panel_title}'.")
                else:
                    optimizations.append(OptimizationResult(
                        panel_title=panel_title,
                        original_query=expr,
                        error="Optimizer returned no result."
                    ))
                    logger.warning(f"Optimizer returned no result for query in '{panel_title}'.")
                    
            except Exception as e:
                logger.error(f"Error optimizing query in '{panel_title}': {e}")
                optimizations.append(OptimizationResult(
                    panel_title=panel_title,
                    original_query=expr,
                    error=f"Error during optimization: {str(e)}"
                ))


def get_panels_to_optimize(panels: List[Dict[str, Any]], count_limit: Optional[int]) -> Generator[Dict[str, Any], None, None]:
    """Yields panels up to the optional count limit, unwrapping rows."""
    has_limit = isinstance(count_limit, int) and count_limit > 0
    processed_count: int = 0
    
    for panel in panels:
        if has_limit and processed_count >= count_limit:  # type: ignore
            break
            
        if panel.get("type") == "row":
            sub_panels = panel.get("panels", [])
            for sub_panel in sub_panels:
                if has_limit and processed_count >= count_limit:  # type: ignore
                    break
                yield sub_panel
                processed_count += 1  # type: ignore
        else:
            yield panel
            processed_count += 1  # type: ignore

@app.post("/optimize-dashboard", response_model=DashboardOptimizeResponse)
async def optimize_dashboard(request: DashboardOptimizeRequest):
    """
    Receives a Grafana dashboard UID, fetches its definition, parses out all PromQL queries,
    and runs them through the optimizer agent.
    """
    logger.info(f"Received optimization request for dashboard UID: {request.dashboard_uid}")
    try:
        dashboard_data = fetch_grafana_dashboard(request.dashboard_uid)
    except ValueError as e:
        logger.error(f"ValueError while processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    dashboard = dashboard_data.get("dashboard", {})
    dashboard_title = dashboard.get("title", "Unknown Dashboard")
    
    logger.info(f"Loaded dashboard: '{dashboard_title}' ({request.dashboard_uid})")
    variables = extract_variables(dashboard_data)
    logger.debug(f"Extracted variables: {variables}")
    optimizations = []
    
    # Clear datasource cache for each new request
    clear_datasource_cache()
    
    panels = dashboard.get("panels", [])
    
    for panel in get_panels_to_optimize(panels, request.panels_count):
        process_panel(panel, variables, optimizations, request.time_range)
            
    logger.info(f"Computed {len(optimizations)} optimizations for dashboard '{dashboard_title}'.")
    return DashboardOptimizeResponse(
        dashboard_title=dashboard_title,
        dashboard_uid=request.dashboard_uid,
        optimizations=optimizations
    )

# For running locally via Python:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
