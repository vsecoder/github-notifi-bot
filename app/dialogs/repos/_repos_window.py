"""``ReposSG.repos`` window — paginated repo list inside the chosen org."""
import operator
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, Window
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
from app.dialogs.repos._helpers import repo_label, user_integrations
from app.dialogs.repos.state import ReposSG, ReposState
from app.utils.dialog_helpers import current_user_for_manager
from app.utils.github_access import (
    invalidate_for_user,
    list_repos_for_org,
)


async def repos_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await current_user_for_manager(dialog_manager)
    config: Config = dialog_manager.middleware_data["config"]
    org = ReposState.load(dialog_manager).selected_org_summary()
    if org is None:
        return {
            "title": "Repos",
            "has_error": True,
            "error": "Missing selection. Go back and pick an org again.",
            "repos": [],
            "count": 0,
        }
    try:
        repos = await list_repos_for_org(user, org, config)
    except Exception as e:
        return {
            "title": f"{org['login']} / repos",
            "has_error": True,
            "error": str(e)[:200],
            "repos": [],
            "count": 0,
        }
    integrated = await user_integrations(dialog_manager)
    decorated = [{**r, "label": repo_label(r, integrated)} for r in repos]
    return {
        "title": f"{org['login']} / repos",
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
    state = ReposState.load(manager)
    state.selected_repo = item_id
    state.save(manager)
    await manager.switch_to(ReposSG.repo_detail)


async def on_repos_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    user = await current_user_for_manager(manager)
    config: Config = manager.middleware_data["config"]
    if user is not None:
        await invalidate_for_user(user, config)
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
