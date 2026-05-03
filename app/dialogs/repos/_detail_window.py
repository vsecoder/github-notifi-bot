"""``ReposSG.repo_detail`` window — info about one repo + Integrate button."""
from typing import Any

from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from app.config import Config
from app.db.functions import Integration
from app.dialogs.repos.state import ReposSG, ReposState
from app.utils.dialog_helpers import current_user_for_manager
from app.utils.github_access import list_repos_for_org


async def repo_detail_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await current_user_for_manager(dialog_manager)
    config: Config = dialog_manager.middleware_data["config"]
    state = ReposState.load(dialog_manager)
    org = state.selected_org_summary()
    full_name = state.selected_repo
    if not (user and org and full_name):
        return {"missing": True, "ok": False, "can_integrate": False}

    repos = await list_repos_for_org(user, org, config)
    repo = next((r for r in repos if r["full_name"] == full_name), None)
    if repo is None:
        return {"missing": True, "ok": False, "can_integrate": False}

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

    source_label = (
        "🔗 GitHub App" if repo["source"] == "app" else "🔑 Personal Access Token"
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
        "source_label": source_label,
    }


repo_detail_window = Window(
    Const("❌ Repo data lost. Go back and pick again.", when="missing"),
    Format(
        "<b>{full_name}</b>\n"
        "{private_label}  •  ⭐ {stars}  •  {admin_label}\n"
        "Source: {source_label}\n"
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
