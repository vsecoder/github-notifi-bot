"""``MyChatsSG.chats`` window — list of chats with the user's integrations."""
import asyncio
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Row,
    ScrollingGroup,
    Select,
)
from aiogram_dialog.widgets.text import Const, Format

from app.db.functions import Integration
from app.dialogs.my_chats._helpers import get_bot
from app.dialogs.my_chats.state import MyChatsSG, MyChatsState
from app.utils.chat_access import invalidate_titles, resolve_chat_title
from app.utils.dialog_helpers import current_user_for_manager


async def chats_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await current_user_for_manager(dialog_manager)
    if user is None:
        return {"empty": True, "chats": []}

    rows = await Integration.filter(user_id=user.id).prefetch_related("chat")
    by_chat: dict[int, list[str]] = {}
    for row in rows:
        try:
            cid = row.chat.chat_id  # type: ignore[union-attr]
        except Exception:
            continue
        by_chat.setdefault(cid, []).append(row.repository_name or "?")

    if not by_chat:
        return {"empty": True, "chats": []}

    bot = await get_bot(dialog_manager)
    titles = await asyncio.gather(
        *[resolve_chat_title(bot, cid) for cid in by_chat]
    )
    chats = [
        {
            "chat_id": cid,
            "title": title,
            "label": f"💬 {title} ({len(repos)})",
        }
        for (cid, repos), title in zip(by_chat.items(), titles)
    ]
    chats.sort(key=lambda c: c["title"].lower())
    return {"empty": False, "chats": chats}


async def on_chat_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    try:
        chat_id = int(item_id)
    except ValueError:
        await callback.answer("Bad chat id.", show_alert=True)
        return
    state = MyChatsState.load(manager)
    state.selected_chat_id = chat_id
    state.save(manager)
    await manager.switch_to(MyChatsSG.chat_detail)


async def on_chats_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    invalidate_titles()
    await callback.answer("Refreshed.")


chats_window = Window(
    Const("💬 <b>Your chats with integrations</b>"),
    Const(
        "\n<i>You don't have any integrations yet.\nAdd me to a group as "
        "administrator and run </i><code>/integrate owner/repo</code><i> "
        "there.</i>",
        when="empty",
    ),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="chat_select",
            item_id_getter=lambda c: str(c["chat_id"]),
            items="chats",
            on_click=on_chat_selected,
        ),
        id="chats_scroll",
        width=1,
        height=8,
        when="chats",
    ),
    Row(
        Button(Const("🔄 Refresh"), id="refresh", on_click=on_chats_refresh),
        Cancel(Const("❎ Close")),
    ),
    state=MyChatsSG.chats,
    getter=chats_getter,
)
