import os
from typing import Dict, Any, Optional, Union
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class PromQLOptimizerAgent:
    """
    An AI agent that acts as an expert PromQL and Thanos query optimizer.
    Uses guidelines provided in a local RAG context file.
    """

    def __init__(self, context_file_path: str = "RAG-CONTEXT.txt", model: str = "models/gemini-2.5-flash-lite"):
        """
        Initializes the optimizer agent.
        
        Args:
            context_file_path (str): The path to the text file containing the RAG context.
            model (str): The Gemini model to use.
        """
        self.system_prompt = self._load_context(context_file_path)
        self.model_name = model
        
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Failed to initialize Gemini client. Ensure GEMINI_API_KEY environment variable is set.")
            
        self.client = genai.Client(api_key=api_key)

    def _load_context(self, file_path: str) -> str:
        """Loads the system prompt from the given file path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Context file not found at {file_path}. Please modify the path or create the file.")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise IOError(f"Error reading context file {file_path}: {e}")

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
        user_message = (
            f"Please analyze and optimize the following PromQL/Thanos query based on the system guidelines.\n\n"
            f"### Query Information\n"
            f"- **Raw Query:** `{raw_query}`\n"
            f"- **Execution Latency:** {latency}\n"
            f"- **Series Cardinality:** {cardinality}\n"
            f"- **Variable Context:** {variable_context}\n\n"
            f"Provide a refactored, optimized version of the query. "
            f"For the explanation, be extremely basic: state only what was changed and why. "
            f"Keep each change and its explanation to a single sentence perfectly. "
            f"Additionally, provide a 'grade' from 1 to 100 for the ORIGINAL query. "
            f"The grade should be based on the severity and number of improvements needed (100 = perfect, 1 = extremely dangerous/inefficient). "
            f"Return the response in a structured JSON format with THREE keys exactly: "
            f"'optimized_query' (containing the refactored code), 'explanation' (containing your short analysis), and 'grade' (an integer)."
        )

        try:
            import json
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
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
