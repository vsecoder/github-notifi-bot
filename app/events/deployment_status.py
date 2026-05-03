"""deployment_status — deployment status transitions."""
from typing import Optional

from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, user_link
from app.events._registry import register


class DeploymentStatus(_Base):
    state: str  # success | failure | error | pending | in_progress | queued
    description: Optional[str] = None
    environment: str
    target_url: Optional[str] = None
    creator: GitHubUser


class Deployment(_Base):
    sha: str
    ref: str
    environment: str
    creator: GitHubUser


class DeploymentStatusEvent(_Base):
    deployment_status: DeploymentStatus
    deployment: Deployment
    repository: Repository
    sender: GitHubUser


_ICON = {
    "success": "✅",
    "failure": "❌",
    "error": "❌",
    "pending": "⏳",
    "queued": "⏳",
    "in_progress": "🔄",
    "inactive": "⚪",
}


def deployment_status_message(
    event: DeploymentStatusEvent, ctx: EventCtx
) -> Optional[str]:
    state = event.deployment_status.state
    icon = _ICON.get(state, "🚢")

    target = ""
    if event.deployment_status.target_url:
        target = (
            f'\n<a href="{event.deployment_status.target_url}">View deployment</a>'
        )

    desc = ""
    if event.deployment_status.description:
        desc = f"\n<i>{_e(event.deployment_status.description)}</i>"

    return (
        f"<b>{icon} Deployment to <code>{_e(event.deployment_status.environment)}</code> "
        f"— {_e(state)} on {repo_link(event.repository)}</b>\n"
        f"By {user_link(event.deployment_status.creator)}"
        f"{desc}{target}"
    )


register(
    "deployment_status", DeploymentStatusEvent, deployment_status_message
)
