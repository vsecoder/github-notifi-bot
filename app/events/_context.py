"""Per-event context passed to formatters."""
from dataclasses import dataclass
from typing import Optional

from app.config import Config


@dataclass
class EventCtx:
    """Context a formatter receives alongside the event payload.

    For follow-up GitHub API calls (e.g. ``commit_message`` fetching diff
    line counts), formatters should use :func:`make_github_client` instead
    of building their own ``Github`` instance — that helper picks the right
    auth path (App-installation vs PAT) automatically.
    """
    # PAT — used only when ``installation_id`` is None (PAT-source events).
    auth_token: Optional[str] = None
    # GitHub App installation id — set for App-source events. When present,
    # ``make_github_client`` uses canonical ``Auth.AppInstallationAuth``
    # instead of treating ``auth_token`` as a generic bearer.
    installation_id: Optional[int] = None
    # Required when ``installation_id`` is set (so the helper can sign JWTs
    # with the App's private key).
    config: Optional[Config] = None


def make_github_client(ctx: EventCtx):
    """Return a PyGithub ``Github`` instance bound to the right auth source,
    or ``None`` if the context has no usable credentials.

    * **App-source** (``installation_id`` + ``config``): uses
      ``GithubIntegration.get_github_for_installation`` — canonical App auth
      that signs JWTs internally and refreshes installation tokens on expiry.
    * **PAT-source** (``auth_token`` only): wraps the token in ``Auth.Token``.
    """
    # Local imports keep the events package import-graph leaner and avoid
    # pulling github_app code paths during module load.
    from github import Auth, Github

    if ctx.installation_id is not None and ctx.config is not None:
        from app.utils.github_app import get_integration

        try:
            gi = get_integration(ctx.config)
            return gi.get_github_for_installation(ctx.installation_id)
        except Exception:
            return None

    if ctx.auth_token:
        try:
            return Github(auth=Auth.Token(ctx.auth_token))
        except Exception:
            return None

    return None
