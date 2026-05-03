"""Token management dialog.

Three screens:
* main          — show current token status + actions (Update / Test / Remove / Close)
* awaiting_token — wait for the user to paste a PAT, validate it, save it
* confirm_remove — confirmation step before wiping the token

The PAT message is auto-deleted right after we read it, so the secret doesn't
linger in the chat history.
"""
from typing import Any

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row
from aiogram_dialog.widgets.text import Const, Format

from app.db.functions import User
from app.utils.hooks import HookError, validate


class TokenSG(StatesGroup):
    main = State()
    awaiting_token = State()
    confirm_remove = State()


def _mask(token: str) -> str:
    if len(token) <= 10:
        return "•" * len(token)
    return f"{token[:5]}…{token[-4:]}"


async def _current_user(manager: DialogManager) -> User | None:
    if manager.event.from_user is None:
        return None
    return await User.get_or_none(telegram_id=manager.event.from_user.id)


async def main_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    user = await _current_user(dialog_manager)
    if user and user.token:
        status = f"✅ Saved (<code>{_mask(user.token)}</code>)"
        return {"status_line": status, "has_token": True}
    return {"status_line": "❌ No token saved.", "has_token": False}


async def awaiting_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    error = dialog_manager.dialog_data.get("error")
    return {"error": error or "", "has_error": bool(error)}


async def on_update_clicked(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    manager.dialog_data.pop("error", None)
    await manager.switch_to(TokenSG.awaiting_token)


async def on_test_clicked(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    user = await _current_user(manager)
    if user is None or not user.token:
        await callback.answer("No token to test.", show_alert=True)
        return
    result = validate(user.token)
    if isinstance(result, HookError):
        snippet = (result.message or "").split("\n", 1)[0][:180]
        await callback.answer(f"❌ {snippet}", show_alert=True)
    else:
        await callback.answer("✅ Token is valid.", show_alert=True)


async def on_remove_clicked(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    await manager.switch_to(TokenSG.confirm_remove)


async def on_remove_confirmed(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    user = await _current_user(manager)
    if user is not None:
        await User.filter(id=user.id).update(token=None)
    await manager.switch_to(TokenSG.main)


async def on_back_to_main(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    manager.dialog_data.pop("error", None)
    await manager.switch_to(TokenSG.main)


async def on_token_message(
    message: Message, _input: MessageInput, manager: DialogManager
) -> None:
    text = (message.text or "").strip()
    # Best-effort delete of the message containing the PAT.
    try:
        await message.delete()
    except Exception:
        pass

    result = validate(text)
    if isinstance(result, HookError):
        manager.dialog_data["error"] = result.message
        return  # stay on awaiting_token; getter will surface the error

    if message.from_user is None:
        manager.dialog_data["error"] = "Couldn't identify your Telegram user."
        return

    user_id = message.from_user.id
    if await User.get_or_none(telegram_id=user_id) is None:
        await User.register(user_id)
    await User.write_token(user_id, text)

    manager.dialog_data.pop("error", None)
    await manager.switch_to(TokenSG.main)


main_window = Window(
    Const("🔑 <b>GitHub Token</b>\n"),
    Format("Status: {status_line}"),
    Row(
        Button(Const("🔄 Update"), id="upd", on_click=on_update_clicked),
        Button(
            Const("🧪 Test"),
            id="tst",
            on_click=on_test_clicked,
            when="has_token",
        ),
    ),
    Button(
        Const("🗑 Remove"),
        id="rm",
        on_click=on_remove_clicked,
        when="has_token",
    ),
    Cancel(Const("❎ Close")),
    state=TokenSG.main,
    getter=main_getter,
)

awaiting_window = Window(
    Const(
        "📥 Send your <b>Personal Access Token</b> as a regular message.\n\n"
        "ℹ️ Required scopes: <code>admin:repo_hook</code> "
        "(and <code>repo</code> for private repositories).\n"
        "🔒 The message will be auto-deleted as soon as I receive it."
    ),
    Format("\n❌ {error}", when="has_error"),
    MessageInput(on_token_message),
    Button(Const("◀️ Cancel"), id="cancel", on_click=on_back_to_main),
    state=TokenSG.awaiting_token,
    getter=awaiting_getter,
)

confirm_remove_window = Window(
    Const(
        "⚠️ Are you sure you want to remove your token?\n\n"
        "Existing webhooks on the GitHub side will keep firing — "
        "but you won't be able to add new integrations or run /reinstall "
        "until you set a new token."
    ),
    Row(
        Button(Const("✅ Yes, remove"), id="yes", on_click=on_remove_confirmed),
        Button(Const("◀️ Cancel"), id="no", on_click=on_back_to_main),
    ),
    state=TokenSG.confirm_remove,
)


token_dialog = Dialog(main_window, awaiting_window, confirm_remove_window)
