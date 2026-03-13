from .base_optimizer import BasePromQLOptimizer
from .query_optimizer import PromQLOptimizerAgent
from .query_optimizer_openai import PromQLOptimizerOpenAIAgent
from .query_optimizer_anthropic import PromQLOptimizerAnthropicAgent

def get_optimizer(optimizer_type: str = "gemini", context_path: str = "RAG-CONTEXT.txt", few_shots_path: str = "few_shots.json") -> BasePromQLOptimizer:
    """
    Factory function to get the correct PromQL optimizer based on the specified type.
    
    Args:
        optimizer_type (str): The type of optimizer to instantiate ('gemini', 'openai', 'anthropic').
        context_path (str): Path to the RAG context file.
        few_shots_path (str): Path to the few-shots JSON file.
        
    Returns:
        BasePromQLOptimizer: An instance of the requested optimizer.
    """
    optimizer_type = optimizer_type.lower()
    
    if optimizer_type == "openai":
        return PromQLOptimizerOpenAIAgent(context_file_path=context_path, few_shots_path=few_shots_path)
    elif optimizer_type == "anthropic":
        return PromQLOptimizerAnthropicAgent(context_file_path=context_path, few_shots_path=few_shots_path)
    elif optimizer_type == "gemini":
        return PromQLOptimizerAgent(context_file_path=context_path, few_shots_path=few_shots_path)
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}. Must be 'gemini', 'openai', or 'anthropic'.")
