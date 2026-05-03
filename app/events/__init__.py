"""GitHub event schemas + Telegram message formatters.

Each event lives in its own module (``push.py``, ``release.py``, …) and
registers itself with the registry on import. Importing this package is
enough to populate the registry — consumers just call ``build_message``.
"""
from app.events._context import EventCtx  # noqa: F401
from app.events._registry import (  # noqa: F401
    EVENT_HANDLERS,
    build_message,
    get_subscribed_events,
)

# Side-effect imports: each module calls ``register(...)`` at module level.
from app.events import (  # noqa: F401
    commit_comment,
    create,
    delete,
    deployment_status,
    discussion,
    discussion_comment,
    fork,
    issue_comment,
    issues,
    member,
    ping,
    public,
    pull_request,
    pull_request_review,
    pull_request_review_comment,
    push,
    release,
    star,
    workflow_run,
)

__all__ = [
    "EVENT_HANDLERS",
    "EventCtx",
    "build_message",
    "get_subscribed_events",
]
