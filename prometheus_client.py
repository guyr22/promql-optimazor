import os
import time
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("promql-optimizer")


def evaluate_promql(query: str, variables: Dict[str, Any], time_range: str = "1h", prometheus_url: Optional[str] = None) -> tuple[Optional[str], int]:
    """
    Substitutes Grafana variables and evaluates the query against Prometheus 
    to get actual latency and cardinality.
    
    Args:
        query: The raw PromQL expression.
        variables: Dashboard variable context for substitution.
        time_range: Time range string for $__range substitution.
        prometheus_url: The Prometheus evaluation endpoint URL.
                        If None, falls back to the global PROMETHEUS_URL.
    
    Returns:
        A tuple of (latency_str, cardinality). latency_str is None if the query fails.
    """
    eval_url = f"{prometheus_url}/api/v1/query"
    logger.debug(f"Evaluating query against Prometheus ({eval_url}): {query}")
    
    substituted_query = query
    # Very basic variable substitution for $var, ${var}, or [[var]]
    for var_name, var_obj in variables.items():
        # Handle complex grafana variable objects (e.g. {'value': ['status'], 'is_multi': True})
        val = var_obj.get("value") if isinstance(var_obj, dict) and "value" in var_obj else var_obj
        
        if isinstance(val, list):
            if "$__all" in val or "all" in [str(v).lower() for v in val]:
                val_str = ".*" # variable might have a regex, we dont consider it right now
            else:
                val_str = "|".join(str(v) for v in val)
        elif str(val) == "$__all" or str(val).lower() == "all":
            val_str = ".*"
        else:
            val_str = str(val)
            
        # Replace occurrences
        safe_val = val_str.replace("$", "$$") # escape for regex replacement if needed, though simple replace is easier
        substituted_query = substituted_query.replace(f"${{{var_name}}}", val_str)
        substituted_query = substituted_query.replace(f"${var_name}", val_str)
        substituted_query = substituted_query.replace(f"[[{var_name}]]", val_str)

    # Substitute $__range with time_range for prometheus evaluation
    prom_query = substituted_query.replace("$__range", time_range).replace("${__range}", time_range)
    
    try:
        start_time = time.time()
        response = requests.get(eval_url, params={"query": prom_query}, timeout=10)
        end_time = time.time()
        
        latency_secs = end_time - start_time
        latency_str = f"{latency_secs:.3f}s"
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            results = data.get("result", [])
            cardinality = len(results)
            logger.debug(f"Query evaluated successfully. Latency: {latency_str}, Cardinality: {cardinality}")
            return latency_str, cardinality
        else:
            logger.error(f"Prometheus returned error {response.status_code}: {response.text}")
            return None, 0
            
    except Exception as e:
        logger.error(f"Exception during Prometheus evaluation: {e}")
        return None, 0
