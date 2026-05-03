"""Free-form text in private chat — dispatcher.

Two paths depending on user state:
  • No PAT yet → try to save the input as their token (legacy convenience;
    the modern flow is via the Connect dialog).
  • Has PAT   → treat the input as a repo name and show its summary.

Slash commands have their own handlers earlier in the router chain; if one
slips through unmatched, we ignore it here.
"""
from aiogram import F, Router
from aiogram.types import Message

from app.db.functions import User
from app.utils.filters import IS_DM
from app.utils.hooks import HookError, check_repo, validate

router = Router()


@router.message(IS_DM, F.text)
async def dm_text_handler(message: Message):
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    if message.from_user is None:
        return

    user = await User.get_or_none(telegram_id=message.from_user.id)
    if user is None:
        await message.answer(
            "You are not registered. Please use /start to register."
        )
        return

    if user.token:
        await _show_repo_summary(message, user.token, text)
    else:
        await _try_save_pat(message, message.from_user.id, text)


async def _show_repo_summary(
    message: Message, token: str, repo_name: str
) -> None:
    repo = check_repo(token, repo_name)
    if isinstance(repo, HookError):
        await message.answer(f"❌ {repo.message}")
        return

    summary = (
        f"📐 <b>{'🔒' if repo.private else ''} "
        f"<a href='https://github.com/{repo.full_name}'>{repo.full_name}</a></b> "
        f"{repo.stargazers_count} ⭐️\n"
        f"<i>{repo.description if repo.description else 'No description'}</i>\n\n"
        f"Run in a group: <code>/integrate {repo.full_name}</code> "
        "to start receiving notifications."
    )
    await message.answer(summary)


async def _try_save_pat(
    message: Message, telegram_user_id: int, text: str
) -> None:
    result = validate(text)
    if isinstance(result, HookError):
        await message.answer(f"❌ {result.message}")
        return

    await User.write_token(telegram_user_id, text)
    await message.answer(
        "✅ Token saved. Use <code>/token &lt;new_token&gt;</code> to replace "
        "it later."
    )
    await message.answer(
        "Now add me as <b>administrator</b> to the group where you want "
        "notifications, and run <code>/integrate username/repository</code> "
        "there.\nYou can also send me a repo name (e.g. "
        "<code>hikariatama/Hikka</code>) to view its summary."
    )
