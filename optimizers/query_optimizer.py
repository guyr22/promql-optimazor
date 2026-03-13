import os
from typing import Dict, Any, Optional, Union
from google import genai
from google.genai import types
from dotenv import load_dotenv

from .base_optimizer import BasePromQLOptimizer

load_dotenv()

class PromQLOptimizerAgent(BasePromQLOptimizer):
    """
    An AI agent that acts as an expert PromQL and Thanos query optimizer.
    Uses guidelines provided in a local RAG context file and Gemini LLM.
    Inherits from BasePromQLOptimizer.
    """

    def __init__(self, context_file_path: str = "RAG-CONTEXT.txt", few_shots_path: str = "few_shots.json", model: str = "gemini-2.5-flash"):
        """
        Initializes the optimizer agent.
        
        Args:
            context_file_path (str): The path to the text file containing the RAG context.
            few_shots_path (str): The path to the JSON file containing few-shot examples.
            model (str): The Gemini model to use.
        """
        super().__init__(context_file_path, few_shots_path, model)
        
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Failed to initialize Gemini client. Ensure GEMINI_API_KEY environment variable is set.")
            
        self.client = genai.Client(api_key=api_key)

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
        contents = []
        import json

        # Add few-shot examples to the context
        for shot in self.few_shots:
            shot_latency = shot.get("performance", {}).get("latency", "unknown")
            shot_cardinality = shot.get("performance", {}).get("cardinality", 0)
            
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=self._format_user_message(
                    shot["raw_query"], 
                    shot["variable_context"], 
                    shot_latency, 
                    shot_cardinality
                ))]
            ))
            contents.append(types.Content(
                role="model",
                parts=[types.Part(text=json.dumps({
                    "optimized_query": shot["optimized_query"],
                    "explanation": shot["explanation"],
                    "grade": shot["grade"]
                }))]
            ))

        # Add the actual user request
        user_message = self._format_user_message(raw_query, variable_context, latency, cardinality)
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.2, # low temperature for more deterministic, analytical responses
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error during LLM API call: {e}")
            return None

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    # Ensure you have your Gemini API key set in your environment:
    # export GEMINI_API_KEY="your-api-key-here"
    
    context_path = "RAG-CONTEXT.txt"
    
    # Check if the real RAG context is present to run the demo locally
    if not os.path.exists(context_path):
        print(f"Please ensure {context_path} is in the same directory.")
    else:
        try:
            # Initialize the agent
            agent = PromQLOptimizerAgent(context_file_path=context_path)
            
            # Dummy Grafana execution data
            dummy_query = 'sum(rate(http_requests_total{job=~"$job", status="500"}[5m])) by (instance)'
            dummy_vars = {"job": "api-server|auth-service", "status": "All"}
            dummy_latency = "18.2s"
            dummy_cardinality = 500000
            
            print("Sending optimization request to LLM...\n")
            
            result = agent.optimize_query(
                raw_query=dummy_query,
                variable_context=dummy_vars,
                latency=dummy_latency,
                cardinality=dummy_cardinality
            )
            
            if result:
                print("=== LLM Response ===")
                print(result)
            else:
                print("Failed to get a response. Check your API key and connection.")
                
        except Exception as err:
            print(f"Execution Error: {err}")
