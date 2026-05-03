"""My-chats dialog — overview of where the user has integrations.

States:

* ``chats``              — list of chats grouped by chat_id, each showing
                           title and repo count.
* ``chat_detail``        — chosen chat: integrations as buttons + Manage
                           events shortcut.
* ``integration_detail`` — single integration screen with Delete action.
* ``events``             — toggle event types for the selected chat (full
                           19-event keyboard, admin-gated, stale-event
                           markers — same logic as the in-group /events).
"""
import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
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
from app.db.functions import EventSetting, Integration, User
from app.db.models import EventType
from app.handlers.user.event_settings import (
    EVENT_LABELS,
    compute_available_events,
)
from app.utils.chat_access import invalidate_titles, resolve_chat_title


class MyChatsSG(StatesGroup):
    chats = State()
    chat_detail = State()
    integration_detail = State()
    events = State()


async def _bot(manager: DialogManager) -> Bot:
    return manager.middleware_data["bot"]


def _config(manager: DialogManager) -> Config:
    return manager.middleware_data["config"]


async def _current_user(manager: DialogManager) -> User | None:
    if manager.event.from_user is None:
        return None
    return await User.get_or_none(telegram_id=manager.event.from_user.id)


async def _is_admin_in_target_chat(
    bot: Bot, chat_id: int, telegram_user_id: int
) -> bool:
    """Verify the user is currently admin in the target chat. Cached
    invalidations live in chat_access; here we hit the API fresh because
    actions (delete, toggle) deserve up-to-date checks."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramAPIError:
        return False
    return telegram_user_id in [a.user.id for a in admins]


# ----- chats window -----

async def chats_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await _current_user(dialog_manager)
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

    bot = await _bot(dialog_manager)
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
        manager.dialog_data["selected_chat_id"] = int(item_id)
    except ValueError:
        await callback.answer("Bad chat id.", show_alert=True)
        return
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


# ----- chat_detail window -----

async def chat_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    chat_id = dialog_manager.dialog_data.get("selected_chat_id")
    user = await _current_user(dialog_manager)
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

    bot = await _bot(dialog_manager)
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
        manager.dialog_data["selected_integration_id"] = int(item_id)
    except ValueError:
        await callback.answer("Bad integration id.", show_alert=True)
        return
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


# ----- integration_detail window -----

async def integration_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    integ_id = dialog_manager.dialog_data.get("selected_integration_id")
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
    chat_id = manager.dialog_data.get("selected_chat_id")
    integ_id = manager.dialog_data.get("selected_integration_id")
    user_tg_id = (
        manager.event.from_user.id if manager.event.from_user else None
    )
    if chat_id is None or integ_id is None or user_tg_id is None:
        await callback.answer("Lost context.", show_alert=True)
        return

    bot = await _bot(manager)
    if not await _is_admin_in_target_chat(bot, chat_id, user_tg_id):
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


# ----- events window -----

def _event_label(s: EventSetting, available: set[str] | None) -> str:
    state = "✅" if s.enabled else "❌"
    label = EVENT_LABELS.get(s.event_type, s.event_type)
    if (
        available is not None
        and s.event_type != "ping"
        and s.event_type not in available
    ):
        return f"⚠️{state} {label}"
    return f"{state} {label}"


async def events_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    chat_id = dialog_manager.dialog_data.get("selected_chat_id")
    if chat_id is None:
        return {"missing": True, "ok": False, "events": [], "title": "?"}

    config = _config(dialog_manager)
    bot = await _bot(dialog_manager)
    title = await resolve_chat_title(bot, chat_id)
    available = await compute_available_events(chat_id, config.api.host)
    settings = await EventSetting.for_chat(chat_id)
    settings = sorted(
        settings,
        key=lambda s: list(EVENT_LABELS).index(s.event_type)
        if s.event_type in EVENT_LABELS
        else len(EVENT_LABELS),
    )

    events = [
        {"event_type": s.event_type, "label": _event_label(s, available)}
        for s in settings
    ]

    stale_banner = ""
    if available is not None:
        all_events = {e.value for e in EventType} - {"ping"}
        if all_events - available:
            stale_banner = (
                "\n\n⚠️ Some events aren't subscribed on the GitHub side. "
                "Run /reinstall in the chat to update."
            )

    return {
        "missing": False,
        "ok": True,
        "title": title,
        "stale_banner": stale_banner,
        "events": events,
    }


async def on_event_toggle(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    chat_id = manager.dialog_data.get("selected_chat_id")
    user_tg_id = (
        manager.event.from_user.id if manager.event.from_user else None
    )
    if chat_id is None or user_tg_id is None:
        await callback.answer("Lost context.", show_alert=True)
        return

    bot = await _bot(manager)
    if not await _is_admin_in_target_chat(bot, chat_id, user_tg_id):
        await callback.answer(
            "You're not a chat administrator anymore.", show_alert=True
        )
        return

    try:
        event_type = EventType(item_id)
    except ValueError:
        await callback.answer("Unknown event type.", show_alert=True)
        return

    config = _config(manager)
    available = await compute_available_events(chat_id, config.api.host)

    setting = await EventSetting.get_or_none(
        chat_id=chat_id, event_type=event_type.value
    )
    if setting is None:
        await callback.answer("Setting not found.", show_alert=True)
        return

    is_stale = (
        available is not None
        and event_type.value != "ping"
        and event_type.value not in available
    )
    if is_stale and not setting.enabled:
        await callback.answer(
            "This event isn't subscribed on the GitHub side. Run /reinstall "
            "in the chat to update webhook subscriptions before enabling it.",
            show_alert=True,
        )
        return

    setting.enabled = not setting.enabled
    await setting.save()
    await callback.answer(
        f"{event_type.value} {'enabled' if setting.enabled else 'disabled'}"
    )


events_window = Window(
    Const("❌ Chat info lost. Go back.", when="missing"),
    Format(
        "✨ <b>Events for {title}</b>{stale_banner}", when="ok"
    ),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="event_select",
            item_id_getter=lambda e: str(e["event_type"]),
            items="events",
            on_click=on_event_toggle,
        ),
        id="events_scroll",
        width=2,
        height=10,
        when="events",
    ),
    Row(
        SwitchTo(
            Const("« Back"), id="back", state=MyChatsSG.chat_detail
        ),
        Cancel(Const("❎ Close")),
    ),
    state=MyChatsSG.events,
    getter=events_getter,
)


my_chats_dialog = Dialog(
    chats_window,
    chat_detail_window,
    integration_detail_window,
    events_window,
)
