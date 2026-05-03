"""discussion — GitHub Discussions: created/closed/reopened/answered."""
from typing import Optional

from app.events._base import _Base, Discussion, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class DiscussionEvent(_Base):
    action: str
    discussion: Discussion
    repository: Repository
    sender: GitHubUser


_INTERESTING = {"created", "closed", "reopened", "answered"}
_ICONS = {"created": "💭", "closed": "🔒", "reopened": "🔓", "answered": "✅"}


def discussion_message(
    event: DiscussionEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action not in _INTERESTING:
        return None
    icon = _ICONS.get(event.action, "💭")
    body = truncate(event.discussion.body, 300)
    body_block = (
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n'
        if body else ""
    )
    return (
        f"<b>{icon} {user_link(event.sender)} {_e(event.action)} discussion "
        f'<a href="{event.discussion.html_url}">#{event.discussion.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.discussion.title)}</i>\n"
        f"{body_block}"
    )


register("discussion", DiscussionEvent, discussion_message)
