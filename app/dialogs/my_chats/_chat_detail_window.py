"""``MyChatsSG.chat_detail`` window — integrations of one chat as buttons."""
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Cancel,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from app.db.functions import Integration
from app.dialogs.my_chats._helpers import get_bot
from app.dialogs.my_chats.state import MyChatsSG, MyChatsState
from app.utils.chat_access import resolve_chat_title
from app.utils.dialog_helpers import current_user_for_manager


async def chat_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    chat_id = MyChatsState.load(dialog_manager).selected_chat_id
    user = await current_user_for_manager(dialog_manager)
    if chat_id is None or user is None:
        return {"missing": True, "ok": False, "integrations": [], "any": False}

    rows = await Integration.filter(
        user_id=user.id, chat__chat_id=chat_id
    ).all()
    integrations = [
        {
            "id": r.id,
            "label": f"🔌 {r.repository_name}",
        }
        for r in rows
    ]

    bot = await get_bot(dialog_manager)
    title = await resolve_chat_title(bot, chat_id)

    return {
        "missing": False,
        "ok": True,
        "title": title,
        "chat_id": chat_id,
        "integrations": integrations,
        "any": bool(integrations),
        "none": not integrations,
    }


async def on_integration_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    try:
        integration_id = int(item_id)
    except ValueError:
        await callback.answer("Bad integration id.", show_alert=True)
        return
    state = MyChatsState.load(manager)
    state.selected_integration_id = integration_id
    state.save(manager)
    await manager.switch_to(MyChatsSG.integration_detail)


chat_detail_window = Window(
    Const("❌ Chat info lost. Go back and pick again.", when="missing"),
    Format(
        "<b>{title}</b>  <i>(id {chat_id})</i>\n\n"
        "🔌 Tap an integration to manage it, or <b>Manage events</b> "
        "to toggle event types.",
        when="any",
    ),
    Format(
        "<b>{title}</b>  <i>(id {chat_id})</i>\n\n"
        "<i>You have no integrations in this chat anymore.</i>",
        when="none",
    ),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="integ_select",
            item_id_getter=lambda i: str(i["id"]),
            items="integrations",
            on_click=on_integration_selected,
        ),
        id="integ_scroll",
        width=1,
        height=8,
        when="any",
    ),
    SwitchTo(
        Const("✏ Manage events"),
        id="goto_events",
        state=MyChatsSG.events,
        when="ok",
    ),
    Row(
        SwitchTo(Const("« Back"), id="back", state=MyChatsSG.chats),
        Cancel(Const("❎ Close")),
    ),
    state=MyChatsSG.chat_detail,
    getter=chat_detail_getter,
)
