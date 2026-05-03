"""delete — branch or tag deleted."""
from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link
from app.events._registry import register


class DeleteEvent(_Base):
    ref: str
    ref_type: str  # branch | tag
    repository: Repository
    sender: GitHubUser


def delete_message(event: DeleteEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🗑 On {repo_link(event.repository)} deleted "
        f"{_e(event.ref_type)} {_e(event.ref)}</b>"
    )


register("delete", DeleteEvent, delete_message)
