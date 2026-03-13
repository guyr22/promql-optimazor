import os
import json
from typing import Dict, Any, Optional, Union, List
from anthropic import Anthropic
from dotenv import load_dotenv

from .base_optimizer import BasePromQLOptimizer

load_dotenv()

class PromQLOptimizerAnthropicAgent(BasePromQLOptimizer):
    """
    An AI agent that acts as an expert PromQL and Thanos query optimizer.
    Uses guidelines provided in a local RAG context file and Anthropic's Claude LLM.
    Inherits from BasePromQLOptimizer.
    """

    def __init__(self, context_file_path: str = "RAG-CONTEXT.txt", few_shots_path: str = "few_shots.json", model: str = "claude-3-7-sonnet-20250219"):
        """
        Initializes the Anthropic optimizer agent.
        
        Args:
            context_file_path (str): The path to the text file containing the RAG context.
            few_shots_path (str): The path to the JSON file containing few-shot examples.
            model (str): The Anthropic model to use.
        """
        super().__init__(context_file_path, few_shots_path, model)
        
        # Configure Anthropic API
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Failed to initialize Anthropic client. Ensure ANTHROPIC_API_KEY environment variable is set.")
            
        self.client = Anthropic(api_key=api_key)

    def optimize_query(
        self, 
        raw_query: str, 
        variable_context: Union[Dict, str], 
        latency: Union[str, float], 
        cardinality: int
    ) -> Optional[Dict[str, str]]:
        """
        Analyzes and optimizes a PromQL/Thanos query based on execution telemetry and dashboard context.

        Args:
            raw_query (str): The templated PromQL query from Grafana.
            variable_context (Union[Dict, str]): The configuration of dashboard variables.
            latency (Union[str, float]): The execution time of the query (e.g., "18.2s").
            cardinality (int): The number of series touched during execution.

        Returns:
            Optional[Dict[str, str]]: A dictionary containing 'optimized_query' and 'explanation'.
        """
        messages = []

        # Add few-shot examples to the context
        for shot in self.few_shots:
            shot_latency = shot.get("performance", {}).get("latency", "unknown")
            shot_cardinality = shot.get("performance", {}).get("cardinality", 0)
            
            messages.append({
                "role": "user",
                "content": self._format_user_message(
                    shot["raw_query"], 
                    shot["variable_context"], 
                    shot_latency, 
                    shot_cardinality
                )
            })
            messages.append({
                "role": "assistant",
                "content": json.dumps({
                    "optimized_query": shot["optimized_query"],
                    "explanation": shot["explanation"],
                    "grade": shot["grade"]
                })
            })

        # Add the actual user request
        user_message = self._format_user_message(raw_query, variable_context, latency, cardinality)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=self.model_name,
                system=self.system_prompt,
                messages=messages,
                temperature=0.2,
                max_tokens=1000
            )
            
            # Extract JSON from the response text
            return json.loads(response.content[0].text)
        except Exception as e:
            print(f"Error during Anthropic API call: {e}")
            return None

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    context_path = "RAG-CONTEXT.txt"
    if not os.path.exists(context_path):
        print(f"Please ensure {context_path} is in the same directory.")
    else:
        try:
            agent = PromQLOptimizerAnthropicAgent(context_file_path=context_path)
            
            dummy_query = 'sum(rate(http_requests_total{job=~"$job", status="500"}[5m])) by (instance)'
            dummy_vars = {"job": "api-server|auth-service", "status": "All"}
            dummy_latency = "18.2s"
            dummy_cardinality = 500000
            
            print("Sending optimization request to Anthropic...\n")
            result = agent.optimize_query(
                raw_query=dummy_query,
                variable_context=dummy_vars,
                latency=dummy_latency,
                cardinality=dummy_cardinality
            )
            
            if result:
                print("=== Anthropic Response ===")
                print(json.dumps(result, indent=2))
            else:
                print("Failed to get a response. Check your API key and connection.")
                
        except Exception as err:
            print(f"Execution Error: {err}")
