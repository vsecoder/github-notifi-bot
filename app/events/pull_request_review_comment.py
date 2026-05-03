"""pull_request_review_comment — line-level comment on a PR diff."""
from typing import Optional

from app.events._base import _Base, Comment, GitHubUser, PullRequest, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class PullRequestReviewCommentEvent(_Base):
    action: str  # created | edited | deleted
    comment: Comment
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser


def pull_request_review_comment_message(
    event: PullRequestReviewCommentEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "created":
        return None

    path = f" <code>{_e(event.comment.path)}</code>" if event.comment.path else ""
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on "
        f'<a href="{event.pull_request.html_url}">PR #{event.pull_request.number}</a>'
        f"{path} in {repo_link(event.repository)}</b>\n"
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register(
    "pull_request_review_comment",
    PullRequestReviewCommentEvent,
    pull_request_review_comment_message,
)
