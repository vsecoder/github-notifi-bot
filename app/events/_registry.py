"""Registry mapping GitHub event names to (schema, formatter).

Each event module calls ``register(name, schema_cls, formatter)`` at import
time; ``app.events.__init__`` imports them all to populate the registry.
"""
import logging
from typing import Callable, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from app.events._context import EventCtx


T = TypeVar("T", bound=BaseModel)
Formatter = Callable[[T, EventCtx], Optional[str]]
_AnyFormatter = Callable[[BaseModel, EventCtx], Optional[str]]

EVENT_HANDLERS: dict[str, tuple[type[BaseModel], _AnyFormatter]] = {}


def register(
    name: str, schema_cls: type[T], formatter: Formatter[T]
) -> None:
    if name in EVENT_HANDLERS:
        raise RuntimeError(f"Event {name!r} is already registered")
    # Variance: each formatter accepts a specific subclass of BaseModel,
    # but we store as the generic signature for uniform dispatch. ``build_message``
    # only ever calls a formatter with an instance of *its* schema_cls, so this
    # is safe at runtime.
    EVENT_HANDLERS[name] = (schema_cls, formatter)  # type: ignore[assignment]


def get_subscribed_events() -> list[str]:
    """Events the bot subscribes to on the GitHub side. ``ping`` is always
    delivered automatically by GitHub on hook creation, so it's excluded."""
    return sorted(name for name in EVENT_HANDLERS if name != "ping")


def build_message(event: str, payload: dict, ctx: EventCtx) -> Optional[str]:
    """Parse the payload via the registered schema and run the formatter.

    Returns None for unknown events, schema-validation failures, or when
    a formatter chooses to skip the event (e.g. uninteresting action sub-type).
    """
    handler = EVENT_HANDLERS.get(event)
    if handler is None:
        return None
    schema_cls, formatter = handler
    try:
        parsed = schema_cls.model_validate(payload)
    except ValidationError as e:
        logging.warning("Schema validation failed for event %s: %s", event, e)
        return None
    try:
        return formatter(parsed, ctx)
    except Exception:
        logging.exception("Formatter failed for event %s", event)
        return None
