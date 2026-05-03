"""create — branch or tag created."""
from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link
from app.events._registry import register


class CreateEvent(_Base):
    ref: str
    ref_type: str  # branch | tag
    repository: Repository
    sender: GitHubUser


def create_message(event: CreateEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🖇 On {repo_link(event.repository)} created a "
        f"{_e(event.ref_type)} {_e(event.ref)}</b>"
    )


register("create", CreateEvent, create_message)
