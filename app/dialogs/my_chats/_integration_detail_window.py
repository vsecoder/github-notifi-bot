"""``MyChatsSG.integration_detail`` window — single integration management."""
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from app.db.functions import Integration
from app.dialogs.my_chats._helpers import get_bot
from app.dialogs.my_chats.state import MyChatsSG, MyChatsState
from app.utils.group_admin import is_user_admin


async def integration_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    integ_id = MyChatsState.load(dialog_manager).selected_integration_id
    if integ_id is None:
        return {"missing": True, "ok": False}
    integration = await Integration.get_by_id(integ_id)
    if integration is None:
        return {"missing": True, "ok": False}
    return {
        "missing": False,
        "ok": True,
        "repo_name": integration.repository_name or "?",
        "auth_source": integration.auth_source,
        "created_at": integration.created_at.strftime("%Y-%m-%d %H:%M UTC"),
    }


async def on_delete_integration(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    state = MyChatsState.load(manager)
    chat_id = state.selected_chat_id
    integ_id = state.selected_integration_id
    user_tg_id = (
        manager.event.from_user.id if manager.event.from_user else None
    )
    if chat_id is None or integ_id is None or user_tg_id is None:
        await callback.answer("Lost context.", show_alert=True)
        return

    bot = await get_bot(manager)
    if not await is_user_admin(bot, chat_id, user_tg_id):
        await callback.answer(
            "You're not a chat administrator anymore (or I lost access "
            "to the chat). Can't delete.",
            show_alert=True,
        )
        return

    integration = await Integration.get_by_id(integ_id)
    if integration is not None:
        await Integration.delete_by_id(integration.id)
        await callback.answer("Integration removed.")
    else:
        await callback.answer("Already deleted.", show_alert=True)

    await manager.switch_to(MyChatsSG.chat_detail)


integration_detail_window = Window(
    Const("❌ Integration data lost. Go back.", when="missing"),
    Format(
        "<b>{repo_name}</b>\n"
        "Added {created_at}\n"
        "Auth source: <code>{auth_source}</code>\n\n"
        "<i>Note: deleting only removes the integration from the bot. "
        "The webhook on the GitHub side stays — clean it up manually in "
        "the repo's Settings → Webhooks if you want it gone there too.</i>",
        when="ok",
    ),
    Button(
        Const("🗑 Delete from chat"),
        id="del",
        on_click=on_delete_integration,
        when="ok",
    ),
    Row(
        SwitchTo(
            Const("« Back to chat"), id="back", state=MyChatsSG.chat_detail
        ),
        Cancel(Const("❎ Close")),
    ),
    state=MyChatsSG.integration_detail,
    getter=integration_detail_getter,
)
