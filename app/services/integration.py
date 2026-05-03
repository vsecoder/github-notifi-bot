"""Core integration logic — shared between the /integrate command (group)
and the dialog-based DM flow.

The function is auth-source agnostic by design: today it builds the webhook
via the user's PAT; the GitHub App migration will plug a different branch
behind the same shape.
"""
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.db.functions import Chat, Integration, User
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
    host: str,
    *,
    skip_admin_check: bool = False,
) -> IntegrationResult:
    """Integrate ``repo_name`` into ``chat_id`` on behalf of ``telegram_user_id``.

    Re-verifies the user is still a chat administrator unless
    ``skip_admin_check`` is set (only safe when the caller verified it
    immediately before, e.g. inside the /integrate command handler).
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
    if user is None or not user.token:
        return IntegrationResult(
            False,
            "You haven't set a GitHub token yet. Tap <b>🔌 Connect</b> "
            "in DM to set one.",
        )

    repo = check_repo(user.token, repo_name)
    if isinstance(repo, HookError):
        return IntegrationResult(False, repo.message)

    existing = await Integration.get_by_chat_and_repo(
        chat_id=chat_id, repo_name=repo_name
    )
    if existing:
        return IntegrationResult(
            False,
            f"<code>{repo_name}</code> is already integrated in this chat.",
        )

    await Chat.ensure_registered(chat_id)

    integration, reused_existing = await Chat.add_integration(
        chat_id=chat_id, user_id=user.id, repository_name=repo_name
    )

    if not reused_existing:
        result = create_webhook(
            host, integration.integration_token, user.token, repo_name
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
