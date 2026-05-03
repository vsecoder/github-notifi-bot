"""pull_request — PR opened/closed/merged/etc."""
from typing import Optional

from app.events._base import _Base, GitHubUser, PullRequest, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class PullRequestEvent(_Base):
    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser


_INTERESTING = {"opened", "closed", "reopened", "ready_for_review"}


def pull_request_message(
    event: PullRequestEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action not in _INTERESTING:
        return None

    action_label = event.action
    icon = "📝"
    if event.action == "closed" and event.pull_request.merged:
        action_label = "merged"
        icon = "🟣"

    body = truncate(event.pull_request.body or "No description", 200)
    return (
        f"<b>{icon} On {repo_link(event.repository)} {action_label} pull request!</b>\n\n"
        f"<i>{_e(event.pull_request.title)}</i>\n"
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n\n'
        f"User: {user_link(event.pull_request.user)}\n\n"
        f'<a href="{event.pull_request.html_url}">#{event.pull_request.number}</a>'
    )


register("pull_request", PullRequestEvent, pull_request_message)
