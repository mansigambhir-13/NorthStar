"""NorthStar exception hierarchy."""


class NorthStarError(Exception):
    """Base exception for all NorthStar errors."""


class InitializationError(NorthStarError):
    """Failed to initialize project context."""


class ContextError(NorthStarError):
    """Error building or loading strategic context."""


class LLMError(NorthStarError):
    """Error communicating with LLM provider."""


class ScanError(NorthStarError):
    """Error during codebase scanning."""


class StateError(NorthStarError):
    """Error with state persistence (SQLite/JSON)."""


class ConfigError(NorthStarError):
    """Invalid or missing configuration."""


class DriftError(NorthStarError):
    """Error in drift detection."""
