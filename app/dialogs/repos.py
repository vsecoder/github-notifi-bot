"""Repos browser dialog.

Five windows on a single ``ReposSG``:

* ``orgs``                — orgs accessible by the user, plus personal namespace.
* ``repos``               — paginated repo list for the selected org.
* ``repo_detail``         — info about one repo + an "Integrate to a chat" button.
* ``choose_chat``         — list of chats where the user is currently admin;
                            picking one performs the integration directly.
* ``integration_result``  — success / failure feedback after the action.
"""
import operator
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
from app.db.functions import Integration, User
from app.services.integration import integrate_repo
from app.utils.chat_access import (
    invalidate_admin_chats,
    invalidate_titles,
    list_admin_chats,
)
from app.utils.github_access import (
    OrgSummary,
    RepoSummary,
    invalidate,
    list_orgs,
    list_repos,
)


class ReposSG(StatesGroup):
    orgs = State()
    repos = State()
    repo_detail = State()
    choose_chat = State()
    integration_result = State()


# ----- helpers -----

async def _user_token(manager: DialogManager) -> str | None:
    if manager.event.from_user is None:
        return None
    user = await User.get_or_none(telegram_id=manager.event.from_user.id)
    return user.token if user else None


async def _user_integrations(manager: DialogManager) -> set[str]:
    """Set of repository_name's the current user has integrated anywhere."""
    if manager.event.from_user is None:
        return set()
    user = await User.get_or_none(telegram_id=manager.event.from_user.id)
    if user is None:
        return set()
    rows = await Integration.filter(user_id=user.id).all()
    return {r.repository_name for r in rows if r.repository_name}


def _org_label(org: OrgSummary) -> str:
    return f"{'👤' if org['is_personal'] else '🏢'} {org['login']}"


def _repo_label(repo: RepoSummary, integrated: set[str]) -> str:
    integ = "✅ " if repo["full_name"] in integrated else ""
    private = "🔒" if repo["private"] else "🔓"
    admin = "" if repo["permissions_admin"] else "⚠️ "
    return f"{integ}{admin}{private} {repo['name']}"


# ----- orgs window -----

async def orgs_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    token = await _user_token(dialog_manager)
    if not token:
        return {"no_token": True, "has_error": False, "orgs": []}
    try:
        orgs = await list_orgs(token)
    except Exception as e:
        return {
            "no_token": False,
            "has_error": True,
            "error": str(e)[:200],
            "orgs": [],
        }
    return {
        "no_token": False,
        "has_error": False,
        "orgs": [{**o, "label": _org_label(o)} for o in orgs],
    }


async def on_org_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    token = await _user_token(manager)
    if not token:
        await callback.answer("No token. Tap 🔌 Connect.", show_alert=True)
        return
    orgs = await list_orgs(token)
    selected = next((o for o in orgs if o["login"] == item_id), None)
    if selected is None:
        await callback.answer("Organisation not found.", show_alert=True)
        return
    manager.dialog_data["selected_org"] = selected["login"]
    manager.dialog_data["selected_personal"] = selected["is_personal"]
    await manager.switch_to(ReposSG.repos)


async def on_orgs_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    token = await _user_token(manager)
    if token:
        invalidate(token)
    await callback.answer("Refreshed.")


orgs_window = Window(
    Const("🏢 <b>Choose where to look</b>"),
    Const(
        "\n❌ You don't have a GitHub token saved. Tap <b>🔌 Connect</b> "
        "on the keyboard to set one.",
        when="no_token",
    ),
    Format("\n❌ Couldn't fetch organisations: {error}", when="has_error"),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="org_select",
            item_id_getter=operator.itemgetter("login"),
            items="orgs",
            on_click=on_org_selected,
        ),
        id="orgs_scroll",
        width=1,
        height=8,
        when="orgs",
    ),
    Row(
        Button(Const("🔄 Refresh"), id="refresh", on_click=on_orgs_refresh),
        Cancel(Const("❎ Close")),
    ),
    state=ReposSG.orgs,
    getter=orgs_getter,
)


# ----- repos window -----

async def repos_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    token = await _user_token(dialog_manager)
    org = dialog_manager.dialog_data.get("selected_org")
    is_personal = dialog_manager.dialog_data.get("selected_personal", False)
    if not token or not org:
        return {
            "title": "Repos",
            "has_error": True,
            "error": "Missing token or org. Go back and pick again.",
            "repos": [],
            "count": 0,
        }
    try:
        repos = await list_repos(token, org, is_personal)
    except Exception as e:
        return {
            "title": f"{org} / repos",
            "has_error": True,
            "error": str(e)[:200],
            "repos": [],
            "count": 0,
        }
    integrated = await _user_integrations(dialog_manager)
    decorated = [{**r, "label": _repo_label(r, integrated)} for r in repos]
    return {
        "title": f"{org} / repos",
        "has_error": False,
        "repos": decorated,
        "count": len(decorated),
    }


async def on_repo_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    manager.dialog_data["selected_repo"] = item_id
    await manager.switch_to(ReposSG.repo_detail)


async def on_repos_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    token = await _user_token(manager)
    if token:
        invalidate(token)
    await callback.answer("Refreshed.")


repos_window = Window(
    Format("<b>{title}</b> — {count} repos"),
    Format("\n❌ {error}", when="has_error"),
    Const(
        "\nLegend: ✅ already integrated  •  🔒 private  •  🔓 public  "
        "•  ⚠️ no admin access",
        when="repos",
    ),
    ScrollingGroup(
        Select(
            Format("{item[label]}"),
            id="repo_select",
            item_id_getter=operator.itemgetter("full_name"),
            items="repos",
            on_click=on_repo_selected,
        ),
        id="repos_scroll",
        width=1,
        height=8,
        when="repos",
    ),
    Row(
        SwitchTo(Const("« Orgs"), id="back", state=ReposSG.orgs),
        Button(Const("🔄 Refresh"), id="refresh", on_click=on_repos_refresh),
    ),
    Cancel(Const("❎ Close")),
    state=ReposSG.repos,
    getter=repos_getter,
)


# ----- repo_detail window -----

async def repo_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    token = await _user_token(dialog_manager)
    org = dialog_manager.dialog_data.get("selected_org")
    is_personal = dialog_manager.dialog_data.get("selected_personal", False)
    full_name = dialog_manager.dialog_data.get("selected_repo")
    if not (token and org and full_name):
        return {"missing": True, "ok": False, "can_integrate": False}

    repos = await list_repos(token, org, is_personal)
    repo = next((r for r in repos if r["full_name"] == full_name), None)
    if repo is None:
        return {"missing": True, "ok": False, "can_integrate": False}

    rows = await Integration.filter(repository_name=full_name).prefetch_related(
        "chat"
    )
    chat_ids = []
    for row in rows:
        try:
            chat_ids.append(row.chat.chat_id)  # type: ignore[union-attr]
        except Exception:
            continue
    integrations_block = (
        "\n".join(f"• <code>chat {cid}</code>" for cid in chat_ids)
        if chat_ids
        else "<i>not integrated yet</i>"
    )

    return {
        "missing": False,
        "ok": True,
        "can_integrate": repo["permissions_admin"],
        "full_name": repo["full_name"],
        "private_label": "🔒 Private" if repo["private"] else "🔓 Public",
        "stars": repo["stars"],
        "admin_label": (
            "✅ Admin"
            if repo["permissions_admin"]
            else "⚠️ No admin (can't install webhook)"
        ),
        "description": repo["description"] or "<i>no description</i>",
        "integrations_block": integrations_block,
    }


repo_detail_window = Window(
    Const("❌ Repo data lost. Go back and pick again.", when="missing"),
    Format(
        "<b>{full_name}</b>\n"
        "{private_label}  •  ⭐ {stars}  •  {admin_label}\n"
        "<i>{description}</i>\n\n"
        "🔌 <b>Integrations:</b>\n{integrations_block}",
        when="ok",
    ),
    SwitchTo(
        Const("➕ Integrate into a chat…"),
        id="goto_choose_chat",
        state=ReposSG.choose_chat,
        when="can_integrate",
    ),
    Row(
        SwitchTo(Const("« Back to repos"), id="back", state=ReposSG.repos),
        Cancel(Const("❎ Close")),
    ),
    state=ReposSG.repo_detail,
    getter=repo_detail_getter,
)


# ----- choose_chat window -----

async def choose_chat_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    if dialog_manager.event.from_user is None:
        return {"no_chats": True, "chats": [], "repo": "?"}
    bot: Bot = dialog_manager.middleware_data["bot"]
    repo = dialog_manager.dialog_data.get("selected_repo") or "?"
    chats = await list_admin_chats(bot, dialog_manager.event.from_user.id)

    # Skip chats where this repo is already integrated.
    already_in = set(
        (await Integration.filter(repository_name=repo).prefetch_related("chat"))
    )
    blocked_chat_ids = set()
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
    repo = manager.dialog_data.get("selected_repo")
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
        host=config.api.host,
    )

    manager.dialog_data["result_success"] = result.success
    manager.dialog_data["result_message"] = result.message
    manager.dialog_data["result_chat_id"] = chat_id

    if result.success:
        # Announce in the target chat too, so other members know.
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


# ----- integration_result window -----

async def integration_result_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    success = dialog_manager.dialog_data.get("result_success", False)
    msg = dialog_manager.dialog_data.get("result_message") or "—"
    return {
        "success": success,
        "fail": not success,
        "message": msg,
    }


integration_result_window = Window(
    Const("🎉 <b>Done!</b>", when="success"),
    Const("❌ <b>Couldn't integrate</b>", when="fail"),
    Format("\n{message}"),
    Row(
        SwitchTo(Const("« Back to repos"), id="back", state=ReposSG.repos),
        Cancel(Const("❎ Close")),
    ),
    state=ReposSG.integration_result,
    getter=integration_result_getter,
)


repos_dialog = Dialog(
    orgs_window,
    repos_window,
    repo_detail_window,
    choose_chat_window,
    integration_result_window,
)
