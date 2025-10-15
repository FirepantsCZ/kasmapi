# Python
"""Custom exception types used across the client library.

To signal recoverable error conditions such as exhausted usage quotas or
insufficient permissions for a requested operation.
"""


class UsageQuotaReachedError(Exception):
    """Raised when the API usage quota has been reached."""


class ApiPermissionError(Exception):
    """Raised when the caller lacks the required permission(s) to perform an operation.

    This usually indicates a permanent failure until credentials or roles
    are updated to grant the necessary access. Retrying without changing
    permissions will continue to fail.
    """
