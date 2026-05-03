"""Token management dialog.

Three screens:
* main          — show current token status + actions (Update / Test / Remove / Close)
* awaiting_token — wait for the user to paste a PAT, validate it, save it
* confirm_remove — confirmation step before wiping the token

The PAT message is auto-deleted right after we read it, so the secret doesn't
linger in the chat history.
"""

from typing import Any, Optional

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, Url
from aiogram_dialog.widgets.text import Const, Format

from app.config import Config
from app.db.functions import Installation, User
from app.utils.dialog_helpers import current_user_for_manager as _current_user
from app.utils.dialog_state import DialogState
from app.utils.github_app import install_url
from app.utils.hooks import HookError, validate


class TokenSG(StatesGroup):
    main = State()
    awaiting_token = State()
    confirm_remove = State()


class TokenState(DialogState):
    """Typed view over TokenSG.dialog_data."""
    error: Optional[str] = None


def _mask(token: str) -> str:
    if len(token) <= 10:
        return "•" * len(token)
    return f"{token[:5]}…{token[-4:]}"


async def main_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    user = await _current_user(dialog_manager)
    config: Config = dialog_manager.middleware_data["config"]

    # PAT status
    if user and user.token:
        pat_line = f"✅ Saved (<code>{_mask(user.token)}</code>)"
        has_token = True
    else:
        pat_line = "❌ No token saved"
        has_token = False

    # GitHub App status
    app_configured = config.github_app.is_configured
    app_url = ""
    if app_configured and dialog_manager.event.from_user is not None:
        try:
            app_url = install_url(config, dialog_manager.event.from_user.id)
        except RuntimeError:
            app_configured = False

    installations: list[Installation] = []
    if user is not None:
        installations = await Installation.for_user(user.id)
    has_app = bool(installations)

    if has_app:
        accounts = ", ".join(f"<code>{i.account_login}</code>" for i in installations)
        app_line = f"✅ Installed for {accounts}"
        install_button_text = "🔗 Add another installation"
    else:
        app_line = "❌ Not installed"
        install_button_text = "🔗 Install GitHub App"

    return {
        "pat_line": pat_line,
        "has_token": has_token,
        "app_configured": app_configured,
        "app_url": app_url,
        "app_line": app_line,
        "has_app": has_app,
        "install_button_text": install_button_text,
    }


async def awaiting_getter(dialog_manager: DialogManager, **_: Any) -> dict[str, Any]:
    error = TokenState.load(dialog_manager).error
    return {"error": error or "", "has_error": bool(error)}


async def on_update_clicked(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    state = TokenState.load(manager)
    state.error = None
    state.save(manager)
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
    state = TokenState.load(manager)
    state.error = None
    state.save(manager)
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

    state = TokenState.load(manager)

    result = validate(text)
    if isinstance(result, HookError):
        state.error = result.message
        state.save(manager)
        return  # stay on awaiting_token; getter will surface the error

    if message.from_user is None:
        state.error = "Couldn't identify your Telegram user."
        state.save(manager)
        return

    user_id = message.from_user.id
    if await User.get_or_none(telegram_id=user_id) is None:
        await User.register(user_id)
    await User.write_token(user_id, text)

    state.error = None
    state.save(manager)
    await manager.switch_to(TokenSG.main)


main_window = Window(
    Const("🔑 <b>GitHub Connection</b>\n"),
    Format("🔗 <b>App:</b> {app_line}", when="app_configured"),
    Format("🔑 <b>PAT:</b> {pat_line}"),
    Row(
        Button(Const("🔄 Update PAT"), id="upd", on_click=on_update_clicked),
        Button(
            Const("🧪 Test PAT"),
            id="tst",
            on_click=on_test_clicked,
            when="has_token",
        ),
    ),
    Button(
        Const("🗑 Remove PAT"),
        id="rm",
        on_click=on_remove_clicked,
        when="has_token",
    ),
    Url(
        text=Format("{install_button_text}"),
        url=Format("{app_url}"),
        id="install_app",
        when="app_configured",
    ),
    Cancel(Const("❎ Close")),
    state=TokenSG.main,
    getter=main_getter,
)

awaiting_window = Window(
    Const(
        "📥 <b>Send your Personal Access Token</b> as a regular message.\n\n"
        "📚 <b>How to create a token:</b>\n"
        "https://telegra.ph/Poluchenie-tokena-GitHub-01-30\n\n"
        "ℹ️ <b>Required scopes:</b>\n"
        "• <code>admin:repo_hook</code> — to manage webhooks (always)\n"
        "• <code>repo</code> — to access private repositories\n\n"
        "🔒 The message containing your token will be auto-deleted as "
        "soon as I receive it."
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
