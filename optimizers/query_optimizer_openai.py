import os
import json
from typing import Dict, Any, Optional, Union, List
from openai import OpenAI
from dotenv import load_dotenv

from .base_optimizer import BasePromQLOptimizer

load_dotenv()

class PromQLOptimizerOpenAIAgent(BasePromQLOptimizer):
    """
    An AI agent that acts as an expert PromQL and Thanos query optimizer.
    Uses guidelines provided in a local RAG context file and OpenAI's LLM.
    Inherits from BasePromQLOptimizer.
    """


    def __init__(self, context_file_path: str = "RAG-CONTEXT.txt", few_shots_path: str = "few_shots.json", model: str = "gpt-4o"):
        """
        Initializes the optimizer agent.
        
        Args:
            context_file_path (str): The path to the text file containing the RAG context.
            few_shots_path (str): The path to the JSON file containing few-shot examples.
            model (str): The OpenAI model to use.
        """
        super().__init__(context_file_path, few_shots_path, model)
        
        # Configure OpenAI API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Failed to initialize OpenAI client. Ensure OPENAI_API_KEY environment variable is set.")
            
        self.client = OpenAI(api_key=api_key)


    def optimize_query(
        self, 
        raw_query: str, 
        variable_context: Union[Dict, str], 
        latency: Union[str, float], 
        cardinality: int,
        panel_description: str = ""
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
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

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
                    shot_cardinality,
                    shot.get("panel_description", "")
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
        user_message = self._format_user_message(raw_query, variable_context, latency, cardinality, panel_description)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error during OpenAI API call: {e}")
            return None
