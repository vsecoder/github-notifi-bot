from dataclasses import dataclass
from typing import Optional, Union

from github import Auth, Github, GithubException
from github import BadCredentialsException, UnknownObjectException
from github.Repository import Repository

from app.events import get_subscribed_events


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


def _hook_url(host: str, endpoint: str) -> str:
    return f"{host}webhook/{endpoint}"


def create_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
) -> Optional[HookError]:
    """Create a GitHub webhook for `integration` repo. Returns None on success."""
    config = {"url": _hook_url(host, endpoint), "content_type": "json"}
    events = get_subscribed_events()
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
        repo.create_hook("web", config, events, active=True)
        return None
    except GithubException as e:
        return _explain(e, integration)


def update_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
) -> Optional[HookError]:
    """Re-sync the GitHub-side webhook event subscription with the bot's
    current list. If a hook with our URL exists, edit it; otherwise create
    a fresh one. Returns None on success."""
    config = {"url": _hook_url(host, endpoint), "content_type": "json"}
    events = get_subscribed_events()
    target_url = config["url"]
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
        existing = None
        for hook in repo.get_hooks():
            if hook.config.get("url", "") == target_url:
                existing = hook
                break

        if existing is not None:
            existing.edit(name="web", config=config, events=events, active=True)
        else:
            repo.create_hook("web", config, events, active=True)
        return None
    except GithubException as e:
        return _explain(e, integration)


def get_subscribed_events_for(
    gh_token: str, integration: str, host: str, endpoint: str
) -> Union[set[str], HookError]:
    """Return the set of events the GitHub webhook is currently subscribed to,
    or a HookError if we can't reach GitHub / the hook doesn't exist."""
    target_url = _hook_url(host, endpoint)
    try:
        g = _gh(gh_token)
        repo = g.get_repo(integration)
        for hook in repo.get_hooks():
            if hook.config.get("url", "") == target_url:
                return set(hook.events or [])
        return HookError(
            "not_found",
            f"No webhook with our URL was found on <code>{integration}</code>. "
            "Use /reinstall to reinstall it.",
        )
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
