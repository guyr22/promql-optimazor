import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union

class BasePromQLOptimizer(ABC):
    """
    Abstract base class for PromQL/Thanos query optimizers.
    Handles loading context, few-shots, and message formatting.
    """

    def __init__(self, context_file_path: str = "RAG-CONTEXT.txt", few_shots_path: str = "few_shots.json", model: str = "") -> None:
        """
        Initializes the base optimizer.
        
        Args:
            context_file_path (str): The path to the text file containing the RAG context.
            few_shots_path (str): The path to the JSON file containing few-shot examples.
            model (str): The name of the LLM model to use.
        """
        super().__init__()
        self.system_prompt = self._load_context(context_file_path)
        self.few_shots = self._load_few_shots(few_shots_path)
        self.model_name = model

    def _load_few_shots(self, file_path: str) -> list:
        """Loads few-shot examples from a JSON file."""
        if not os.path.exists(file_path):
            print(f"Warning: Few-shots file not found at {file_path}. Proceeding without shots.")
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading few-shots: {e}")
            return []

    def _load_context(self, file_path: str) -> str:
        """Loads the system prompt from the given file path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Context file not found at {file_path}. Please modify the path or create the file.")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            raise IOError(f"Error reading context file {file_path}: {e}")

    def _format_user_message(self, raw_query: str, variable_context: Any, latency: Any, cardinality: Any) -> str:
        """Formats the input data into the user message string."""
        return (
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

    @abstractmethod
    def optimize_query(
        self, 
        raw_query: str, 
        variable_context: Union[Dict, str], 
        latency: Union[str, float], 
        cardinality: int
    ) -> Optional[Dict[str, str]]:
        """
        Analyzes and optimizes a PromQL/Thanos query based on execution telemetry and dashboard context.
        Must be implemented by subclasses.
        """
        pass
