# [TRACEABILITY] REQ-301
# Cloned from: github.com/DeadManOfficial/token-optimization
from .prompt_optimizers import PromptOptimizer
from .response_cache import ResponseCache
from .output_controller import OutputController
from .context_manager import ContextManager
from .request_consolidator import RequestConsolidator
from .token_optimizer_class import TokenOptimizer

__all__ = [
    'TokenOptimizer',
    'PromptOptimizer',
    'ResponseCache',
    'OutputController',
    'ContextManager',
    'RequestConsolidator',
    'optimize_for_claude',
    'optimize_system_prompt',
    'create_template'
]

def optimize_for_claude(prompt: str, max_words: int = 200) -> str:
    """Quick optimization for Claude API"""
    optimizer = TokenOptimizer()
    return optimizer.optimize_prompt(prompt, compress=True, max_words=max_words)


def optimize_system_prompt(prompt: str) -> str:
    """Quick system prompt optimization"""
    return PromptOptimizer.optimize_system_prompt(prompt)


def create_template(task: str) -> str:
    """Get efficient template"""
    return PromptOptimizer.create_efficient_template(task)
