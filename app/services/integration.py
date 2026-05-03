"""Core integration logic — shared between the /integrate command (group)
and the dialog-based DM flow.

Auto-routes between two auth sources:

* **App path** — if the user has a GitHub App installation whose account
  matches the repo's owner, we just bind the integration to that
  installation. No webhook is created (the App-level webhook handles it).

* **PAT path** — fallback: validate the repo via PyGithub, install the
  webhook on the repo via the user's PAT, store the integration_token.
"""
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.config import Config
from app.db.functions import Chat, Installation, Integration, User
from app.db.models import AuthSource
from app.utils.github_access import list_repos_for_installation
from app.utils.hooks import HookError, check_repo, create_webhook


@dataclass
class IntegrationResult:
    success: bool
    message: str  # HTML, safe to send to Telegram


async def integrate_repo(
    bot: Bot,
    chat_id: int,
    telegram_user_id: int,
    repo_name: str,
    config: Config,
    *,
    skip_admin_check: bool = False,
) -> IntegrationResult:
    """Integrate ``repo_name`` into ``chat_id`` on behalf of ``telegram_user_id``.

    Re-verifies the user is still a chat administrator unless
    ``skip_admin_check`` is set (only safe when the caller verified it
    immediately before).
    """
    if not skip_admin_check:
        try:
            admins = await bot.get_chat_administrators(chat_id)
        except TelegramAPIError:
            return IntegrationResult(
                False,
                "I don't have access to that chat anymore. Make sure I'm "
                "still a member there.",
            )
        if telegram_user_id not in [a.user.id for a in admins]:
            return IntegrationResult(
                False, "You're no longer an administrator in that chat."
            )

    user = await User.get_or_none(telegram_id=telegram_user_id)
    if user is None:
        return IntegrationResult(
            False,
            "You're not registered. Send /start to me in private chat first.",
        )

    # Already integrated in this chat?
    existing = await Integration.get_by_chat_and_repo(
        chat_id=chat_id, repo_name=repo_name
    )
    if existing:
        return IntegrationResult(
            False,
            f"<code>{repo_name}</code> is already integrated in this chat.",
        )

    # Decide auth path: prefer App if any installation matches the repo owner.
    repo_owner = repo_name.split("/", 1)[0] if "/" in repo_name else None
    matching_install: Installation | None = None
    if config.github_app.is_configured and repo_owner:
        installations = await Installation.for_user(user.id)
        matching_install = next(
            (i for i in installations if i.account_login == repo_owner),
            None,
        )

    if matching_install is not None:
        return await _integrate_via_app(
            chat_id, user, repo_name, matching_install, config
        )

    if user.token:
        return await _integrate_via_pat(
            chat_id, user, repo_name, config
        )

    return IntegrationResult(
        False,
        "You're not authorized with GitHub yet. Tap <b>🔌 Connect</b> in DM "
        "to install the GitHub App or set a Personal Access Token.",
    )


async def _integrate_via_app(
    chat_id: int,
    user: User,
    repo_name: str,
    installation: Installation,
    config: Config,
) -> IntegrationResult:
    # Verify the App installation can actually see this repo (the user
    # might not have granted it access).
    try:
        repos = await list_repos_for_installation(
            config, installation.installation_id
        )
    except Exception as e:
        return IntegrationResult(
            False,
            f"Couldn't verify App access to <code>{repo_name}</code>: {e}",
        )
    if not any(r["full_name"] == repo_name for r in repos):
        return IntegrationResult(
            False,
            f"<code>{repo_name}</code> isn't part of the App installation "
            f"on <code>{installation.account_login}</code>. "
            "Add it via GitHub → Settings → Applications → "
            f"<code>{installation.account_login}</code> → Configure → "
            "<i>Repository access</i>.",
        )

    await Chat.ensure_registered(chat_id)
    chat = await Chat.get(chat_id=chat_id)

    await Integration.create(
        chat=chat,
        user=user,
        repository_name=repo_name,
        integration_token=None,
        auth_source=AuthSource.app.value,
        installation=installation,
    )

    return IntegrationResult(
        True,
        f"✅ Repository <code>{repo_name}</code> integrated via GitHub App. "
        "Notifications will arrive in the chat.",
    )


async def _integrate_via_pat(
    chat_id: int,
    user: User,
    repo_name: str,
    config: Config,
) -> IntegrationResult:
    repo = check_repo(user.token, repo_name)
    if isinstance(repo, HookError):
        return IntegrationResult(False, repo.message)

    await Chat.ensure_registered(chat_id)

    integration, reused_existing = await Chat.add_integration(
        chat_id=chat_id, user_id=user.id, repository_name=repo_name
    )

    if not reused_existing:
        result = create_webhook(
            config.api.host,
            integration.integration_token,
            user.token,
            repo_name,
        )
        if isinstance(result, HookError):
            await Integration.delete_by_id(integration.id)
            return IntegrationResult(
                False,
                f"Couldn't create the webhook for <code>{repo_name}</code>.\n\n"
                f"{result.message}",
            )

    return IntegrationResult(
        True,
        f"✅ Repository <code>{repo_name}</code> integrated. "
        "Notifications will arrive in the chat.",
    )
