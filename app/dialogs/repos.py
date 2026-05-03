"""Repos browser dialog.

Three windows on a single ``ReposSG``:

* ``orgs``         — list of orgs accessible by the user's PAT, plus
                     personal namespace; tap to drill in.
* ``repos``        — paginated list of repos in the selected org; integrated
                     repos get a ✅ marker.
* ``repo_detail``  — info about one repo, copyable ``/integrate`` command, and
                     the chats it's already wired to.
"""
import operator
from typing import Any

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Cancel,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format

from app.db.functions import Integration, User
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
        return {
            "no_token": True,
            "has_error": False,
            "orgs": [],
        }
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
        "orgs": [
            {**o, "label": _org_label(o)} for o in orgs
        ],
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
        }
    try:
        repos = await list_repos(token, org, is_personal)
    except Exception as e:
        return {
            "title": f"{org} / repos",
            "has_error": True,
            "error": str(e)[:200],
            "repos": [],
        }
    integrated = await _user_integrations(dialog_manager)
    decorated = [
        {**r, "label": _repo_label(r, integrated)} for r in repos
    ]
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
        return {"missing": True, "ok": False}

    repos = await list_repos(token, org, is_personal)
    repo = next((r for r in repos if r["full_name"] == full_name), None)
    if repo is None:
        return {"missing": True, "ok": False}

    # Where is this repo integrated by ANY user?
    rows = await Integration.filter(repository_name=full_name).prefetch_related(
        "chat"
    )
    chat_lines = []
    for row in rows:
        try:
            chat_id = row.chat.chat_id  # type: ignore[union-attr]
            chat_lines.append(f"• <code>chat {chat_id}</code>")
        except Exception:
            continue
    integrations_block = (
        "\n".join(chat_lines) if chat_lines else "<i>not integrated yet</i>"
    )

    return {
        "missing": False,
        "ok": True,
        "full_name": repo["full_name"],
        "private_label": "🔒 Private" if repo["private"] else "🔓 Public",
        "stars": repo["stars"],
        "admin_label": "✅ Admin" if repo["permissions_admin"] else "⚠️ No admin (can't install webhook)",
        "description": repo["description"] or "<i>no description</i>",
        "integrations_block": integrations_block,
        "command": f"/integrate {repo['full_name']}",
    }


repo_detail_window = Window(
    Const("❌ Repo data lost. Go back and pick again.", when="missing"),
    Format(
        "<b>{full_name}</b>\n"
        "{private_label}  •  ⭐ {stars}  •  {admin_label}\n"
        "<i>{description}</i>\n\n"
        "🔌 <b>Integrations:</b>\n{integrations_block}\n\n"
        "📋 <b>Command to run in your group</b> "
        "(long-press to copy, then send it as a chat admin):\n"
        "<code>{command}</code>",
        when="ok",
    ),
    Row(
        SwitchTo(Const("« Back to repos"), id="back", state=ReposSG.repos),
        Cancel(Const("❎ Close")),
    ),
    state=ReposSG.repo_detail,
    getter=repo_detail_getter,
)


repos_dialog = Dialog(orgs_window, repos_window, repo_detail_window)
