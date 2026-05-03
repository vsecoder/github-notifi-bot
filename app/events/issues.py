"""issues — issue opened/closed/reopened/etc."""
from typing import Optional

from app.events._base import _Base, GitHubUser, Issue, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, user_link
from app.events._registry import register


class IssuesEvent(_Base):
    action: str
    issue: Issue
    repository: Repository
    sender: GitHubUser


_INTERESTING = {"opened", "closed", "reopened", "assigned"}


def issue_message(event: IssuesEvent, ctx: EventCtx) -> Optional[str]:
    if event.action not in _INTERESTING:
        return None
    return (
        f"<b>📌 On {repo_link(event.repository)} {_e(event.action)} issue!</b>\n\n"
        f"<i>{_e(event.issue.title)}</i>\n"
        f'<a href="{event.issue.html_url}">#{event.issue.number}</a> by '
        f"{user_link(event.issue.user)}"
    )


register("issues", IssuesEvent, issue_message)
