"""Domain exceptions mapped to HTTP responses in main.py."""


class TargetNotFoundError(Exception):
    """Raised when a monitored target does not exist."""


class DuplicateTargetError(Exception):
    """Raised when a target with the same name already exists."""
