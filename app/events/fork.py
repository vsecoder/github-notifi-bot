"""fork — repo forked."""
from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link
from app.events._registry import register


class ForkEvent(_Base):
    forkee: Repository
    repository: Repository
    sender: GitHubUser


def fork_message(event: ForkEvent, ctx: EventCtx) -> str:
    return (
        f"<b>🍴 {repo_link(event.repository)} forked</b>\n\n"
        f"<i>Total forks count is now:</i> <code>{event.repository.forks}</code>\n"
        f'<i>Fork link:</i> <a href="{event.forkee.html_url}">'
        f"{_e(event.forkee.full_name)}</a>"
    )


register("fork", ForkEvent, fork_message)
