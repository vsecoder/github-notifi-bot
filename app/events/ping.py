"""ping — fired once when GitHub creates the webhook."""
from app.events._base import _Base, Repository
from app.events._context import EventCtx
from app.events._formatting import repo_link
from app.events._registry import register


class PingEvent(_Base):
    repository: Repository


def ping_message(event: PingEvent, ctx: EventCtx) -> str:
    return f"🏓 Repo {repo_link(event.repository)} connected and sending ping!"


register("ping", PingEvent, ping_message)
