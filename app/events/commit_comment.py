"""commit_comment — comment on a specific commit (outside PR review)."""
from typing import Optional

from app.events._base import _Base, Comment, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class CommitCommentEvent(_Base):
    action: str  # created
    comment: Comment
    repository: Repository
    sender: GitHubUser


def commit_comment_message(
    event: CommitCommentEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "created":
        return None
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on a commit in "
        f"{repo_link(event.repository)}</b>\n"
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register("commit_comment", CommitCommentEvent, commit_comment_message)
