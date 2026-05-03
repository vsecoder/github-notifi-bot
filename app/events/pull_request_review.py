"""pull_request_review — someone submitted a review on a PR."""
from typing import Optional

from app.events._base import _Base, GitHubUser, PullRequest, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class Review(_Base):
    state: str  # approved | changes_requested | commented | dismissed
    body: Optional[str] = None
    html_url: str
    user: GitHubUser


class PullRequestReviewEvent(_Base):
    action: str  # submitted | edited | dismissed
    review: Review
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser


def pull_request_review_message(
    event: PullRequestReviewEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "submitted":
        return None

    icon, verb = {
        "approved": ("✅", "approved"),
        "changes_requested": ("🔴", "requested changes on"),
        "commented": ("💬", "commented on"),
        "dismissed": ("⚪", "dismissed review on"),
    }.get(event.review.state, ("📝", event.review.state))

    body_block = ""
    if event.review.body:
        body_block = (
            f'<blockquote expandable="expandable">'
            f"{_e(truncate(event.review.body, 300))}"
            f"</blockquote>\n"
        )

    return (
        f"<b>{icon} {user_link(event.review.user)} {verb} "
        f'<a href="{event.pull_request.html_url}">PR #{event.pull_request.number}</a> '
        f"on {repo_link(event.repository)}</b>\n"
        f"<i>{_e(event.pull_request.title)}</i>\n"
        f"{body_block}"
        f'<a href="{event.review.html_url}">View review</a>'
    )


register("pull_request_review", PullRequestReviewEvent, pull_request_review_message)
