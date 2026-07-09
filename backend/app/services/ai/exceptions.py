class AIError(Exception):
    """Base exception for all AI client/orchestration errors."""
    pass


class ProviderAPIError(AIError):
    """Raised when an external API (like OpenRouter, Groq, HF, USDA) returns a non-200 or fails."""
    pass


class ParsingError(AIError):
    """Raised when the response text cannot be parsed or JSON extracted."""
    pass


class AIOrchestrationError(AIError):
    """Raised when all active providers in the orchestrator chain fail."""
    pass