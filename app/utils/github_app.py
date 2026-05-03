"""GitHub App auth helpers.

Provides:
* lazy ``GithubIntegration`` (signs JWT to talk as the App)
* installation token cache (~58 minutes TTL — Telegram-side calls during
  webhook delivery should be cheap)
* state HMAC for the install flow — encodes the Telegram user_id into the
  install URL so the Setup-URL callback can attribute the new installation
  to the right user
* webhook-signature verification (``X-Hub-Signature-256``)
"""
import base64
import hashlib
import hmac
import threading
import time
from pathlib import Path
from typing import Optional

from github import Auth, GithubIntegration

from app.config import Config


_integration_lock = threading.Lock()
_integration_cache: dict[int, GithubIntegration] = {}  # app_id -> GithubIntegration
_token_lock = threading.Lock()
_token_cache: dict[int, tuple[str, float]] = {}  # installation_id -> (token, exp_ts)


def _load_pem(path: Path) -> str:
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.read_text()


def get_integration(config: Config) -> GithubIntegration:
    """Lazily build (and cache) the GithubIntegration for this App."""
    if not config.github_app.is_configured:
        raise RuntimeError(
            "GitHub App is not configured (set [github_app] in config.toml)."
        )
    app_id = config.github_app.app_id
    with _integration_lock:
        cached = _integration_cache.get(app_id)
        if cached is not None:
            return cached
        pem = _load_pem(Path(config.github_app.private_key_path))
        gi = GithubIntegration(auth=Auth.AppAuth(app_id=app_id, private_key=pem))
        _integration_cache[app_id] = gi
        return gi


def get_installation_token(config: Config, installation_id: int) -> str:
    """Mint or reuse an installation token. Tokens live ~1 hour; we keep
    them in-memory until they're within 60 s of expiry."""
    now = time.time()
    with _token_lock:
        cached = _token_cache.get(installation_id)
        if cached and cached[1] > now + 60:
            return cached[0]

    gi = get_integration(config)
    access = gi.get_access_token(installation_id)
    expires_at = access.expires_at.timestamp()

    with _token_lock:
        _token_cache[installation_id] = (access.token, expires_at)
    return access.token


def get_account_for_installation(config: Config, installation_id: int) -> str:
    """Return the GitHub login (user / org) the installation lives on.

    PyGithub's ``Installation`` object doesn't reliably expose ``.account``
    across versions — we hit the raw REST endpoint and read it from JSON.
    Returns ``"?"`` if the call fails; the ``installation.created`` webhook
    event will backfill the value when it arrives anyway.
    """
    gi = get_integration(config)
    # ``requester`` is the recommended public attribute in PyGithub 2.x;
    # name-mangled fallback covers older versions.
    requester = getattr(gi, "requester", None) or getattr(
        gi, "_GithubIntegration__requester", None
    )
    if requester is None:
        return "?"
    try:
        _, data = requester.requestJsonAndCheck(
            "GET", f"/app/installations/{installation_id}"
        )
    except Exception:
        return "?"
    if not isinstance(data, dict):
        return "?"
    account = data.get("account") or {}
    return str(account.get("login") or "?")


def invalidate_token(installation_id: int) -> None:
    with _token_lock:
        _token_cache.pop(installation_id, None)


# ---------- install URL state ----------

def _state_key(config: Config) -> bytes:
    """Secret used to sign state. We piggy-back on webhook_secret since both
    are the same trust boundary (whoever has the secret can speak to the bot
    as if from GitHub)."""
    secret = config.github_app.webhook_secret
    if not secret:
        raise RuntimeError(
            "github_app.webhook_secret is empty — set it before generating "
            "install URLs."
        )
    return secret.encode()


def sign_state(config: Config, telegram_user_id: int) -> str:
    """HMAC-sign the user id and pack it into a URL-safe blob suitable for
    the ``state`` query parameter on the install URL."""
    payload = str(telegram_user_id).encode()
    sig = hmac.new(_state_key(config), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b":" + sig).decode().rstrip("=")


def verify_state(config: Config, state: str) -> Optional[int]:
    """Verify and unpack a previously-signed state. Returns the
    ``telegram_user_id`` or None if the state is forged / corrupt."""
    try:
        padded = state + "=" * (-len(state) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode())
        payload, sig = decoded.rsplit(b":", 1)
        expected = hmac.new(_state_key(config), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        return int(payload)
    except Exception:
        return None


def install_url(config: Config, telegram_user_id: int) -> str:
    """Build the user-specific install URL with state baked in."""
    state = sign_state(config, telegram_user_id)
    return (
        f"https://github.com/apps/{config.github_app.slug}"
        f"/installations/new?state={state}"
    )


# ---------- webhook signature ----------

def verify_webhook_signature(
    config: Config, body: bytes, signature_header: Optional[str]
) -> bool:
    """Verify GitHub's ``X-Hub-Signature-256`` header against the App's
    webhook secret. Returns True iff the body is genuine."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    secret = config.github_app.webhook_secret
    if not secret:
        return False
    expected = (
        "sha256="
        + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature_header)
