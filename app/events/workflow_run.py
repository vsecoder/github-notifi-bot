"""workflow_run — GitHub Actions workflow finished."""
from typing import Optional

from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, user_link
from app.events._registry import register


class WorkflowRun(_Base):
    name: str
    html_url: str
    head_branch: Optional[str] = None
    head_sha: str
    status: str
    conclusion: Optional[str] = None
    run_attempt: int = 1
    actor: GitHubUser


class WorkflowRunEvent(_Base):
    action: str  # requested | in_progress | completed
    workflow_run: WorkflowRun
    repository: Repository
    sender: GitHubUser


_ICON_BY_CONCLUSION = {
    "success": "✅",
    "failure": "❌",
    "cancelled": "⚪",
    "skipped": "⏭",
    "timed_out": "⌛",
    "action_required": "⚠️",
    "neutral": "➖",
}


def workflow_run_message(
    event: WorkflowRunEvent, ctx: EventCtx
) -> Optional[str]:
    if event.action != "completed":
        return None

    run = event.workflow_run
    icon = _ICON_BY_CONCLUSION.get(run.conclusion or "", "ℹ️")
    branch = f":{_e(run.head_branch)}" if run.head_branch else ""
    attempt = f" (attempt #{run.run_attempt})" if run.run_attempt > 1 else ""
    return (
        f"<b>{icon} Workflow <i>{_e(run.name)}</i> "
        f"{_e(run.conclusion or run.status)} on {repo_link(event.repository)}{branch}</b>\n"
        f"By {user_link(run.actor)}{attempt}\n"
        f'<a href="{run.html_url}">View run</a>'
    )


register("workflow_run", WorkflowRunEvent, workflow_run_message)
