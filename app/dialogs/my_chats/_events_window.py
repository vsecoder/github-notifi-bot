"""``MyChatsSG.events`` window — toggle event types for the selected chat."""
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

from app.db.functions import EventSetting
from app.db.models import EventType
from app.dialogs.my_chats._helpers import get_bot, get_config
from app.dialogs.my_chats.state import MyChatsSG, MyChatsState
from app.handlers.user.event_settings import (
    EVENT_LABELS,
    compute_available_events,
)
from app.utils.chat_access import resolve_chat_title
from app.utils.group_admin import is_user_admin


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
    chat_id = MyChatsState.load(dialog_manager).selected_chat_id
    if chat_id is None:
        return {"missing": True, "ok": False, "events": [], "title": "?"}

    config = get_config(dialog_manager)
    bot = await get_bot(dialog_manager)
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
    chat_id = MyChatsState.load(manager).selected_chat_id
    user_tg_id = (
        manager.event.from_user.id if manager.event.from_user else None
    )
    if chat_id is None or user_tg_id is None:
        await callback.answer("Lost context.", show_alert=True)
        return

    bot = await get_bot(manager)
    if not await is_user_admin(bot, chat_id, user_tg_id):
        await callback.answer(
            "You're not a chat administrator anymore.", show_alert=True
        )
        return

    try:
        event_type = EventType(item_id)
    except ValueError:
        await callback.answer("Unknown event type.", show_alert=True)
        return

    config = get_config(manager)
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
