class BKAMError(Exception):
    """Base class for every error raised by this library."""


class ConfigurationError(BKAMError):
    """The client was set up incorrectly (for example, no API key)."""


class BKAMConnectionError(BKAMError):
    """The API could not be reached (network failure or timeout)."""


class APIError(BKAMError):
    """The API answered with an error status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(APIError):
    """The subscription key is missing or invalid (HTTP 401)."""


class RateLimitError(APIError):
    """Too many requests (HTTP 429)."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        retry_after: float | None = None,
    ):
        super().__init__(message, status_code)
        self.retry_after = retry_after