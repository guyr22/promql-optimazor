import os
import logging
import requests
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger("promql-optimizer")

# Configuration for Grafana
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")

# Cache for datasource info to avoid redundant API calls within the same request
_datasource_cache: Dict[str, Optional[Dict[str, Any]]] = {}


def clear_datasource_cache():
    """Clears the datasource cache. Should be called at the start of each request."""
    _datasource_cache.clear()


def fetch_grafana_dashboard(uid: str) -> Dict[str, Any]:
    """Fetches the dashboard JSON payload from Grafana HTTP API."""
    logger.info(f"Fetching Grafana dashboard with UID: {uid}")
    if not GRAFANA_API_KEY:
        logger.error("GRAFANA_API_KEY environment variable is not set")
        raise ValueError("GRAFANA_API_KEY environment variable is not set")
        
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{GRAFANA_URL.rstrip('/')}/api/dashboards/uid/{uid}"
    
    logger.debug(f"Requesting Grafana API: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch dashboard. Status: {response.status_code}, Response: {response.text}")
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


def resolve_datasource_ref(datasource_ref: Any, variables: Dict[str, Any]) -> Optional[str]:
    """
    Resolves a datasource reference to a UID string.
    Handles objects like {"uid": "abc", "type": "prometheus"},
    plain string UIDs/names, and Grafana variable references like ${DS_PROMETHEUS}.
    """
    if datasource_ref is None:
        return None

    uid = None
    if isinstance(datasource_ref, dict):
        uid = datasource_ref.get("uid")
    elif isinstance(datasource_ref, str):
        uid = datasource_ref
    else:
        return None

    if not uid:
        return None

    # Substitute Grafana variables (e.g. ${DS_PROMETHEUS} or $DS_PROMETHEUS)
    for var_name, var_obj in variables.items():
        val = var_obj.get("value") if isinstance(var_obj, dict) and "value" in var_obj else var_obj
        if isinstance(val, list):
            val_str = str(val[0]) if val else ""
        else:
            val_str = str(val) if val is not None else ""
        uid = uid.replace(f"${{{var_name}}}", val_str)
        uid = uid.replace(f"${var_name}", val_str)

    return uid if uid else None


def fetch_datasource_info(datasource_uid: str) -> Optional[Dict[str, Any]]:
    """
    Fetches datasource details from the Grafana HTTP API by UID.
    Returns the datasource info dict or None on failure.
    Results are cached per UID.
    """
    if datasource_uid in _datasource_cache:
        return _datasource_cache[datasource_uid]

    if not GRAFANA_API_KEY:
        logger.warning("GRAFANA_API_KEY not set; cannot resolve datasource.")
        _datasource_cache[datasource_uid] = None
        return None

    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{GRAFANA_URL.rstrip('/')}/api/datasources/uid/{datasource_uid}"
    logger.info(f"Fetching datasource info for UID: {datasource_uid}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            info = response.json()
            _datasource_cache[datasource_uid] = info
            return info
        else:
            logger.warning(f"Failed to fetch datasource '{datasource_uid}'. Status: {response.status_code}")
            _datasource_cache[datasource_uid] = None
            return None
    except Exception as e:
        logger.error(f"Exception fetching datasource '{datasource_uid}': {e}")
        _datasource_cache[datasource_uid] = None
        return None


def get_prometheus_url(datasource_ref: Any, variables: Dict[str, Any]) -> Optional[str]:
    """
    Given a target's datasource reference, verifies it is a Prometheus datasource.
    Returns None to use the fallback PROMETHEUS_URL for evaluation.
    Returns "NOT_PROMETHEUS" if the datasource is not of type prometheus.
    
    Note: The datasource URL from Grafana is typically an internal network address
    (e.g. http://prometheus:9090) that is not reachable from outside the cluster.
    We only use the datasource info for type verification.
    """
    uid = resolve_datasource_ref(datasource_ref, variables)
    if not uid:
        return None

    ds_info = fetch_datasource_info(uid)
    if not ds_info:
        logger.warning(f"Could not fetch datasource info for UID '{uid}'; will use fallback.")
        return None

    ds_type = ds_info.get("type", "")
    if ds_type != "prometheus":
        logger.info(f"Datasource '{uid}' is of type '{ds_type}', not prometheus. Skipping.")
        return "NOT_PROMETHEUS"

    logger.info(f"Datasource '{uid}' confirmed as prometheus type.")
    return ds_info.get("url")
