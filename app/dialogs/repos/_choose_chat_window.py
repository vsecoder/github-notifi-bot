"""``ReposSG.choose_chat`` window — pick a target chat for the integration."""
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from app.config import Config
from app.db.functions import Integration
from app.dialogs.repos.state import ReposSG, ReposState
from app.services.integration import integrate_repo
from app.utils.chat_access import (
    invalidate_admin_chats,
    invalidate_titles,
    list_admin_chats,
)


async def choose_chat_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    if dialog_manager.event.from_user is None:
        return {"no_chats": True, "chats": [], "repo": "?"}
    bot: Bot = dialog_manager.middleware_data["bot"]
    repo = ReposState.load(dialog_manager).selected_repo or "?"
    chats = await list_admin_chats(bot, dialog_manager.event.from_user.id)

    already_in = await Integration.filter(
        repository_name=repo
    ).prefetch_related("chat")
    blocked_chat_ids: set[int] = set()
    for row in already_in:
        try:
            blocked_chat_ids.add(row.chat.chat_id)  # type: ignore[union-attr]
        except Exception:
            pass

    decorated = [
        {
            "chat_id": c["chat_id"],
            "title": c["title"],
            "label": (
                f"✓ {c['title']} (already integrated)"
                if c["chat_id"] in blocked_chat_ids
                else f"💬 {c['title']}"
            ),
            "blocked": c["chat_id"] in blocked_chat_ids,
        }
        for c in chats
    ]
    available = [c for c in decorated if not c["blocked"]]
    return {
        "no_chats": not chats,
        "all_blocked": bool(chats) and not available,
        "chats": available,
        "repo": repo,
    }


async def on_chat_chosen(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    bot: Bot = manager.middleware_data["bot"]
    config: Config = manager.middleware_data["config"]
    state = ReposState.load(manager)
    repo = state.selected_repo
    if manager.event.from_user is None or repo is None:
        await callback.answer("Lost context.", show_alert=True)
        return
    try:
        chat_id = int(item_id)
    except ValueError:
        await callback.answer("Bad chat id.", show_alert=True)
        return

    result = await integrate_repo(
        bot=bot,
        chat_id=chat_id,
        telegram_user_id=manager.event.from_user.id,
        repo_name=repo,
        config=config,
    )

    state.result_success = result.success
    state.result_message = result.message
    state.save(manager)

    if result.success:
        actor = callback.from_user
        actor_link = (
            f'<a href="tg://user?id={actor.id}">'
            f"@{actor.username or actor.first_name}</a>"
        )
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Repository <code>{repo}</code> integrated by "
                    f"{actor_link}.\n"
                    "Use /events to configure event types."
                ),
            )
        except TelegramAPIError:
            pass

    await manager.switch_to(ReposSG.integration_result)


async def on_choose_chat_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    if manager.event.from_user is not None:
        invalidate_admin_chats(manager.event.from_user.id)
    invalidate_titles()
    await callback.answer("Refreshed.")


choose_chat_window = Window(
    Format(
        "<b>Pick a chat to integrate <code>{repo}</code> into</b>\n"
        "Only chats where I'm a member <i>and</i> you're an administrator "
        "are listed."
    ),
    Const(
        "\n<i>I'm not in any chats with you yet, or you're not an admin "
        "anywhere I'm in. Add me to a group as administrator and tap Refresh.</i>",
        when="no_chats",
    ),
    Const(
        "\n<i>This repo is already integrated in every chat you have. "
        "Use /delete in the chat to remove it.</i>",
        when="all_blocked",
    ),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="chat_select",
            item_id_getter=lambda c: str(c["chat_id"]),
            items="chats",
            on_click=on_chat_chosen,
        ),
        id="choose_chat_scroll",
        width=1,
        height=8,
        when="chats",
    ),
    Row(
        SwitchTo(
            Const("« Back to repo"), id="back", state=ReposSG.repo_detail
        ),
        Button(
            Const("🔄 Refresh"), id="refresh", on_click=on_choose_chat_refresh
        ),
    ),
    Cancel(Const("❎ Close")),
    state=ReposSG.choose_chat,
    getter=choose_chat_getter,
)
