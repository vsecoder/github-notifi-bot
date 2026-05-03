"""star — repo starred / unstarred."""
from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import repo_link, user_link
from app.events._registry import register


class StarEvent(_Base):
    action: str  # created | deleted
    repository: Repository
    sender: GitHubUser


def star_message(event: StarEvent, ctx: EventCtx) -> str:
    verb = "added" if event.action == "created" else "removed"
    return (
        f"<b>⭐️ On {repo_link(event.repository)} {verb} star!</b>\n\n"
        f"Total stars: <i>{event.repository.stargazers_count}</i>\n"
        f"User: {user_link(event.sender)}"
    )


register("star", StarEvent, star_message)
