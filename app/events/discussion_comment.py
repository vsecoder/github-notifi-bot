"""discussion_comment — comments on a discussion."""
from typing import Optional

from app.events._base import _Base, Comment, Discussion, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class DiscussionCommentEvent(_Base):
    action: str
    comment: Comment
    discussion: Discussion
    repository: Repository
    sender: GitHubUser


def discussion_comment_message(
    event: DiscussionCommentEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "created":
        return None
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on discussion "
        f'<a href="{event.discussion.html_url}">#{event.discussion.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.discussion.title)}</i>\n"
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register(
    "discussion_comment", DiscussionCommentEvent, discussion_comment_message
)
