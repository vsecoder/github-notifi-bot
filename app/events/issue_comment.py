"""issue_comment — comments on issues AND on PRs (without code line)."""
from typing import Optional

from app.events._base import _Base, Comment, GitHubUser, Issue, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class IssueCommentEvent(_Base):
    action: str  # created | edited | deleted
    comment: Comment
    issue: Issue
    repository: Repository
    sender: GitHubUser


def issue_comment_message(
    event: IssueCommentEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "created":
        return None

    is_pr = event.issue.pull_request is not None
    label = "PR" if is_pr else "issue"
    body = truncate(event.comment.body, 300)
    return (
        f"<b>💬 {user_link(event.comment.user)} commented on "
        f'<a href="{event.issue.html_url}">{label} #{event.issue.number}</a> '
        f"in {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.issue.title)}</i>\n"
        f'<blockquote expandable="expandable">{_e(body)}</blockquote>\n'
        f'<a href="{event.comment.html_url}">View comment</a>'
    )


register("issue_comment", IssueCommentEvent, issue_comment_message)
