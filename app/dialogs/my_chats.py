"""My-chats dialog — read-only overview of where the user has integrations.

Two windows:

* ``chats``       — list of chats grouped by chat_id, each showing title and
                    repo count.
* ``chat_detail`` — chosen chat with its integrated repos.

Removal stays in-group (``/delete owner/repo``) — DM removal would need an
admin re-check at apply-time which is outside the scope of a read-only view.
"""
import asyncio
import operator
import time
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

from app.db.functions import Integration, User


class MyChatsSG(StatesGroup):
    chats = State()
    chat_detail = State()


# Chat title cache: {chat_id: (title, expires_at)}
_TITLE_TTL = 300.0
_title_cache: dict[int, tuple[str, float]] = {}


async def _resolve_chat_title(bot: Bot, chat_id: int) -> str:
    cached = _title_cache.get(chat_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]
    try:
        tg_chat = await bot.get_chat(chat_id)
        title = (
            tg_chat.title
            or (tg_chat.full_name if hasattr(tg_chat, "full_name") else None)
            or f"chat {chat_id}"
        )
    except TelegramAPIError:
        title = f"(unavailable, id={chat_id})"
    _title_cache[chat_id] = (title, now + _TITLE_TTL)
    return title


def invalidate_titles() -> None:
    _title_cache.clear()


async def _bot(manager: DialogManager) -> Bot:
    return manager.middleware_data["bot"]


async def _current_user(manager: DialogManager) -> User | None:
    if manager.event.from_user is None:
        return None
    return await User.get_or_none(telegram_id=manager.event.from_user.id)


# ----- chats window -----

async def chats_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await _current_user(dialog_manager)
    if user is None:
        return {"empty": True, "no_user": True, "chats": []}

    rows = await Integration.filter(user_id=user.id).prefetch_related("chat")
    by_chat: dict[int, list[str]] = {}
    for row in rows:
        try:
            cid = row.chat.chat_id  # type: ignore[union-attr]
        except Exception:
            continue
        by_chat.setdefault(cid, []).append(row.repository_name or "?")

    if not by_chat:
        return {"empty": True, "no_user": False, "chats": []}

    bot = await _bot(dialog_manager)
    titles = await asyncio.gather(
        *[_resolve_chat_title(bot, cid) for cid in by_chat]
    )
    chats = [
        {
            "chat_id": cid,
            "title": title,
            "repos_count": len(repos),
            "repos": repos,
            "label": f"💬 {title} ({len(repos)})",
        }
        for (cid, repos), title in zip(by_chat.items(), titles)
    ]
    chats.sort(key=lambda c: c["title"].lower())
    return {"empty": False, "no_user": False, "chats": chats}


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
        "\n<i>You don't have any integrations yet.\nAdd me to a group "
        "as administrator and run </i><code>/integrate owner/repo</code><i>"
        " there.</i>",
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
        return {"missing": True, "ok": False}

    rows = await Integration.filter(
        user_id=user.id, chat__chat_id=chat_id
    ).all()
    repo_lines = "\n".join(
        f"• <code>{r.repository_name}</code>" for r in rows
    ) or "<i>no integrations</i>"

    bot = await _bot(dialog_manager)
    title = await _resolve_chat_title(bot, chat_id)

    return {
        "missing": False,
        "ok": True,
        "title": title,
        "chat_id": chat_id,
        "repos_block": repo_lines,
    }


chat_detail_window = Window(
    Const("❌ Chat info lost. Go back and pick again.", when="missing"),
    Format(
        "<b>{title}</b>  <i>(id {chat_id})</i>\n\n"
        "🔌 <b>Integrations you set up here:</b>\n{repos_block}\n\n"
        "<i>To remove or change settings, run "
        "</i><code>/integrations</code><i>, "
        "</i><code>/delete owner/repo</code><i> or </i><code>/events</code>"
        "<i> in that chat.</i>",
        when="ok",
    ),
    Row(
        SwitchTo(Const("« Back"), id="back", state=MyChatsSG.chats),
        Cancel(Const("❎ Close")),
    ),
    state=MyChatsSG.chat_detail,
    getter=chat_detail_getter,
)


my_chats_dialog = Dialog(chats_window, chat_detail_window)
