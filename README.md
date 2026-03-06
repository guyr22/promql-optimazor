# PromQL Optimizer Agent

A sophisticated, AI-driven backend service designed to automatically analyze and optimize Prometheus (PromQL) and Thanos queries extracted from Grafana dashboards. The service evaluates queries against a live Prometheus instance to calculate real latency and cardinality, and then uses a Large Language Model (Google Gemini API) to suggest refactoring improvements based on best practices.

## Features

- **Grafana Integration**: Give it a Dashboard UID, and it will fetch the dashboard, extract the panels, resolve variables, and process every PromQL query inside.
- **Prometheus Validation**: Evaluates queries against a live Prometheus TSDB to append real execution latency and series cardinality to the AI context.
- **RAG-Powered Optimization**: Uses a customizable local `RAG-CONTEXT.txt` file to enforce strict SRE guidelines (e.g., regex avoidance, vector matching rules).
- **Heuristic Grading**: The Agent judges the original query and assigns it a performance score from 1-100 based on how dangerous or inefficient it is.
- **Mock Service Testing**: Includes a Python-based Prometheus exporter (`mock-service.py`) designed to simulate high-cardinality traffic for local testing.

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (for local infrastructure)

## Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/guyr22/promql-optimazor.git
   cd promql-optimazor
   ```

2. **Set up the virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root of the project with your API keys:
   ```env
   GEMINI_API_KEY="your-gemini-api-key"
   GRAFANA_API_KEY="your-grafana-service-account-token"
   ```

4. **Start the Infrastructure:**
   ```bash
   docker-compose up -d
   ```
   This will start Grafana (port 3000), Prometheus (port 9090), Postgres, and the mock metrics generator (port 8001).

5. **Start the FastAPI Server:**
   ```bash
   python api.py
   ```
   The API will be available at `http://localhost:8000`.

## Usage

Send a POST request to the `/optimize-dashboard` endpoint with a `dashboard_uid` that exists in your Grafana instance.

```bash
curl -X POST http://localhost:8000/optimize-dashboard \
  -H "Content-Type: application/json" \
  -d '{"dashboard_uid": "your_dashboard_uid"}'
```

### Example Output
```json
{
  "dashboard_title": "My Dashboard",
  "dashboard_uid": "xyz123",
  "optimizations": [
    {
      "panel_title": "Traffic Panel",
      "original_query": "mock_http_requests_total{endpoint=~\".*\"}",
      "optimized_query": "mock_http_requests_total{endpoint!=\"\"}",
      "explanation": "Removed the inefficient wildcard regex and replaced it with a non-empty string matcher.",
      "grade": 40,
      "error": null
    }
  ]
}
```

## Configuration (RAG Context)
You can customize the rules the AI agent follows by modifying the `RAG-CONTEXT.txt` file. The optimizer dynamically reads this file on every request, so changes are applied instantly without restarting the server.
