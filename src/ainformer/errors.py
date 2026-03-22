class AInformerError(Exception):
    """Base application exception."""


class ConfigurationError(AInformerError):
    """Raised when registry or source configuration is invalid."""


class SourceNotFoundError(AInformerError):
    """Raised when a requested source id does not exist."""


class SourceDisabledError(AInformerError):
    """Raised when a source is disabled."""


class AdapterNotImplementedError(AInformerError):
    """Raised when a source has no concrete adapter implementation."""


class AdapterMethodMismatchError(AInformerError):
    """Raised when the selected acquisition method is not supported by the adapter."""


class SourceFetchError(AInformerError):
    """Raised when a source fails during runtime fetching or parsing."""
