"""
Utils models package.

Models are organized into logical groups:
- mixins: Base model mixins for common functionality
- notification: Email and SMS notification models
- security: Request fingerprinting and security models
- lighthouse: Performance monitoring models
- search: Full-text search models
- llms: LLM usage tracking models
"""

# Import base model mixins
# Import lighthouse models
from .lighthouse import LighthouseAudit

# Import LLM models
from .llms import LLMUsage
from .mixins import SoftDeleteModel, TimestampedModel

# Import all notification models
from .notification import Email, NotificationConfig, NotificationEmail, NotificationPhoneNumber, TextMessage

# Import all search models
from .search import SearchableContent

# Import all security models
from .security import HTTPStatusCode, IPAddress, RequestFingerprint

__all__ = [
    # Base model mixins
    "TimestampedModel",
    "SoftDeleteModel",
    # Notification models
    "NotificationConfig",
    "NotificationEmail",
    "NotificationPhoneNumber",
    "Email",
    "TextMessage",
    # Security models
    "HTTPStatusCode",
    "IPAddress",
    "RequestFingerprint",
    # Lighthouse models
    "LighthouseAudit",
    # Search models
    "SearchableContent",
    # LLM models
    "LLMUsage",
]
