"""public — repo switched from private to public."""
from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import repo_link, user_link
from app.events._registry import register


class PublicEvent(_Base):
    repository: Repository
    sender: GitHubUser


def public_message(event: PublicEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🔓 {repo_link(event.repository)} is now public!</b>\n"
        f"By {user_link(event.sender)}"
    )


register("public", PublicEvent, public_message)
