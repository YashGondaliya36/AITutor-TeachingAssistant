"""
LLM Model Tiering System
Phase 6: AI Efficiency - Model Tiering

Routes requests to appropriate model tiers based on complexity.
Uses faster/cheaper models for simple tasks, reserves powerful models for complex ones.
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ComplexityTier(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"          # Quick responses, greetings, simple Q&A
    MODERATE = "moderate"      # Content explanation, hints
    COMPLEX = "complex"        # Detailed grading, multi-step reasoning
    CRITICAL = "critical"      # Final assessments, important decisions


class ModelTier(Enum):
    """Available model tiers (fastest to slowest)"""
    FAST = "fast"             # Gemini Flash, GPT-3.5-turbo
    STANDARD = "standard"     # Gemini Pro
    ADVANCED = "advanced"     # Gemini Pro 1.5, GPT-4
    PREMIUM = "premium"       # GPT-4-turbo, Claude Opus


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: str  # "google", "openai", "anthropic"
    max_tokens: int
    cost_per_1k_tokens: float
    avg_latency_ms: int
    capabilities: list[str]


# Model tier configurations
MODEL_CONFIGS: Dict[ModelTier, ModelConfig] = {
    ModelTier.FAST: ModelConfig(
        name="gemini-1.5-flash",
        provider="google",
        max_tokens=8192,
        cost_per_1k_tokens=0.00015,  # $0.15 per 1M tokens
        avg_latency_ms=200,
        capabilities=["chat", "simple_grading", "hints"]
    ),
    ModelTier.STANDARD: ModelConfig(
        name="gemini-1.5-pro",
        provider="google",
        max_tokens=32768,
        cost_per_1k_tokens=0.0005,  # $0.50 per 1M tokens
        avg_latency_ms=400,
        capabilities=["chat", "grading", "hints", "explanations"]
    ),
    ModelTier.ADVANCED: ModelConfig(
        name="gemini-1.5-pro",
        provider="google",
        max_tokens=1000000,  # Experimental long context
        cost_per_1k_tokens=0.001,
        avg_latency_ms=800,
        capabilities=["chat", "grading", "hints", "explanations", "detailed_feedback", "multi_step"]
    ),
    ModelTier.PREMIUM: ModelConfig(
        name="gpt-4-turbo",
        provider="openai",
        max_tokens=128000,
        cost_per_1k_tokens=0.01,  # $10 per 1M tokens
        avg_latency_ms=1500,
        capabilities=["all"]
    )
}


# Complexity to tier mapping
TASK_TIER_MAPPING: Dict[ComplexityTier, ModelTier] = {
    ComplexityTier.SIMPLE: ModelTier.FAST,
    ComplexityTier.MODERATE: ModelTier.STANDARD,
    ComplexityTier.COMPLEX: ModelTier.ADVANCED,
    ComplexityTier.CRITICAL: ModelTier.PREMIUM
}


class ModelRouter:
    """
    Routes LLM requests to appropriate model tiers.
    Optimizes for cost and latency while maintaining quality.
    """
    
    def __init__(self):
        self.usage_stats: Dict[ModelTier, Dict[str, int]] = {
            tier: {"calls": 0, "tokens": 0, "errors": 0}
            for tier in ModelTier
        }
    
    def classify_task_complexity(
        self,
        task_type: str,
        context_length: int = 0,
        requires_reasoning: bool = False,
        is_final_assessment: bool = False
    ) -> ComplexityTier:
        """
        Classify task complexity based on characteristics.
        
        Args:
            task_type: Type of task ("greeting", "grading", "explanation", etc.)
            context_length: Length of context in tokens
            requires_reasoning: Whether task needs multi-step reasoning
            is_final_assessment: Whether this is a critical assessment
        
        Returns:
            ComplexityTier classification
        """
        # Critical tasks always use premium
        if is_final_assessment:
            return ComplexityTier.CRITICAL
        
        # Long context or complex reasoning requires advanced
        if context_length > 8000 or requires_reasoning:
            return ComplexityTier.COMPLEX
        
        # Simple task classification
        simple_tasks = {"greeting", "acknowledgment", "simple_hint", "yes_no"}
        if task_type in simple_tasks and context_length < 1000:
            return ComplexityTier.SIMPLE
        
        # Default to moderate
        return ComplexityTier.MODERATE
    
    def select_model(
        self,
        complexity: ComplexityTier,
        fallback_enabled: bool = True
    ) -> ModelConfig:
        """
        Select appropriate model for complexity level.
        
        Args:
            complexity: Task complexity tier
            fallback_enabled: Whether to fallback to next tier if unavailable
        
        Returns:
            Selected ModelConfig
        """
        tier = TASK_TIER_MAPPING[complexity]
        model_config = MODEL_CONFIGS[tier]
        
        logger.info(f"Selected {model_config.name} for {complexity.value} task")
        
        return model_config
    
    def route_request(
        self,
        task_type: str,
        prompt: str,
        context_length: Optional[int] = None,
        **kwargs
    ) -> tuple[ModelConfig, ComplexityTier]:
        """
        Route request to appropriate model.
        
        Args:
            task_type: Type of task
            prompt: The prompt text
            context_length: Optional context length (auto-calculated if None)
            **kwargs: Additional parameters
        
        Returns:
            Tuple of (ModelConfig, ComplexityTier)
        """
        if context_length is None:
            # Rough token estimation: 1 token ~= 4 characters
            context_length = len(prompt) // 4
        
        # Classify task
        complexity = self.classify_task_complexity(
            task_type=task_type,
            context_length=context_length,
            requires_reasoning=kwargs.get('requires_reasoning', False),
            is_final_assessment=kwargs.get('is_final_assessment', False)
        )
        
        # Select model
        model = self.select_model(complexity)
        
        # Update stats
        self.usage_stats[TASK_TIER_MAPPING[complexity]]["calls"] += 1
        
        return model, complexity
    
    def estimate_cost(
        self,
        tier: ModelTier,
        input_tokens: int,
        output_tokens: int = 1000
    ) -> float:
        """
        Estimate cost for using a specific tier.
        
        Args:
            tier: Model tier
            input_tokens: Number of input tokens
            output_tokens: Estimated output tokens
        
        Returns:
            Estimated cost in USD
        """
        config = MODEL_CONFIGS[tier]
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * config.cost_per_1k_tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_calls = sum(stats["calls"] for stats in self.usage_stats.values())
        
        # Calculate distribution
        distribution = {
            tier.value: {
                "calls": stats["calls"],
                "percentage": (stats["calls"] / total_calls * 100) if total_calls > 0 else 0
            }
            for tier, stats in self.usage_stats.items()
        }
        
        return {
            "total_calls": total_calls,
            "tier_distribution": distribution,
            "raw_stats": self.usage_stats
        }


# Global router instance
_model_router = ModelRouter()


def route_llm_request(task_type: str, prompt: str, **kwargs) -> tuple[ModelConfig, ComplexityTier]:
    """
    Global function to route LLM requests.
    
    Usage:
        model, complexity = route_llm_request(
            task_type="grading",
            prompt="Grade this answer: ...",
            requires_reasoning=True
        )
        
        # Use the selected model
        response = call_llm(prompt, model=model.name)
    """
    return _model_router.route_request(task_type, prompt, **kwargs)


def get_routing_stats() -> Dict[str, Any]:
    """Get model routing statistics"""
    return _model_router.get_stats()


# Example usage:
"""
# 1. Simple greeting - uses FAST model
model, tier = route_llm_request(
    task_type="greeting",
    prompt="Hello! How can I help you today?"
)
# Returns: gemini-1.5-flash (FAST tier)

# 2. Grading with reasoning - uses ADVANCED model
model, tier = route_llm_request(
    task_type="grading",
    prompt="Grade this complex math proof...",
    requires_reasoning=True,
    context_length=5000
)
# Returns: gemini-1.5-pro with long context (ADVANCED tier)

# 3. Final assessment - uses PREMIUM model
model, tier = route_llm_request(
    task_type="grading",
    prompt="Final exam grading...",
    is_final_assessment=True
)
# Returns: gpt-4-turbo (PREMIUM tier)

# 4. Cost estimation
fast_cost = _model_router.estimate_cost(ModelTier.FAST, input_tokens=500, output_tokens=200)
premium_cost = _model_router.estimate_cost(ModelTier.PREMIUM, input_tokens=500, output_tokens=200)
print(f"Fast tier: ${fast_cost:.4f}")
print(f"Premium tier: ${premium_cost:.4f}")
print(f"Savings: ${premium_cost - fast_cost:.4f} per request")

# 5. View statistics
stats = get_routing_stats()
print(f"Total LLM calls: {stats['total_calls']}")
print(f"FAST tier: {stats['tier_distribution']['fast']['percentage']:.1f}%")
print(f"STANDARD tier: {stats['tier_distribution']['standard']['percentage']:.1f}%")

# Expected distribution for cost optimization:
# FAST: ~60-70% (greetings, simple hints)
# STANDARD: ~20-30% (explanations, basic grading)
# ADVANCED: ~5-10% (complex grading)
# PREMIUM: <5% (final assessments only)
"""
