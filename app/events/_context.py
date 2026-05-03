"""Per-event context passed to formatters."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class EventCtx:
    """Per-event context (e.g. the user's GitHub token for follow-up API calls)."""
    user_token: Optional[str] = None
