from dataclasses import dataclass
from typing import Optional, Union

from github import Auth, Github, GithubException
from github import BadCredentialsException, UnknownObjectException
from github.Repository import Repository


@dataclass
class HookError:
    code: str  # auth | not_found | no_permission | exists | unknown
    message: str
    detail: Optional[str] = None


def _gh(token: str) -> Github:
    return Github(auth=Auth.Token(token))


def _explain(e: GithubException, repo_name: str = "") -> HookError:
    status = getattr(e, "status", None)
    data = e.data if isinstance(e.data, dict) else {}
    api_msg = data.get("message", "")

    if isinstance(e, BadCredentialsException) or status == 401:
        return HookError(
            "auth",
            "Your GitHub token is invalid or expired. Send a new one in DM via /token.",
            api_msg,
        )

    if isinstance(e, UnknownObjectException) or status == 404:
        target = repo_name or "the requested resource"
        return HookError(
            "not_found",
            f"Repository <code>{target}</code> not found, or your token doesn't have "
            "access to it.\n"
            "• Check the spelling: <code>username/repository</code>.\n"
            "• For <b>private</b> repos your token must have the <code>repo</code> scope.",
            api_msg,
        )

    if status == 403:
        return HookError(
            "no_permission",
            "GitHub denied the request. Common reasons:\n"
            "• Your token is missing the <code>admin:repo_hook</code> scope "
            "(required to manage webhooks).\n"
            "• You are <b>not the owner</b> of the repository and don't have "
            "admin/maintain access — only owners or admins can install webhooks.\n"
            "• You hit the GitHub API rate limit. Try again later.",
            api_msg,
        )

    if status == 422 and "already exists" in api_msg.lower():
        return HookError(
            "exists",
            "A webhook with the same URL already exists on this repository.",
            api_msg,
        )

    return HookError(
        "unknown",
        f"GitHub API error ({status}): {api_msg or 'unknown'}",
        str(data),
    )


def create_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
) -> Optional[HookError]:
    """Create a GitHub webhook for `integration` repo. Returns None on success."""
    config = {
        "url": f"{host}webhook/{endpoint}",
        "content_type": "json",
    }
    events = ["push", "pull_request", "issues", "fork", "star", "create"]
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
        repo.create_hook("web", config, events, active=True)
        return None
    except GithubException as e:
        return _explain(e, integration)


def validate(token: str) -> Union[bool, HookError]:
    """Validate a GitHub PAT. Returns True on success or HookError on failure."""
    if not (token.startswith("ghp_") or token.startswith("github_pat_")):
        return HookError(
            "auth",
            "Token format looks wrong. Use a Personal Access Token that starts "
            "with <code>ghp_</code> (classic) or <code>github_pat_</code> (fine-grained).",
        )
    try:
        g = _gh(token)
        _ = g.get_user().login
        return True
    except GithubException as e:
        return _explain(e)


def check_repo(token: str, repo: str) -> Union[Repository, HookError]:
    """Return the Repository, or HookError on failure."""
    try:
        g = _gh(token)
        return g.get_repo(repo)
    except GithubException as e:
        return _explain(e, repo)


def get_repos(token: str) -> Union[list, HookError]:
    try:
        g = _gh(token)
        return list(g.get_user().get_repos())
    except GithubException as e:
        return _explain(e)
