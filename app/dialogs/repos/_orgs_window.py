"""``ReposSG.orgs`` window — list of accounts the user can browse."""
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
)
from aiogram_dialog.widgets.text import Const, Format

from app.config import Config
from app.dialogs.repos._helpers import org_label
from app.dialogs.repos.state import ReposSG, ReposState
from app.utils.dialog_helpers import current_user_for_manager
from app.utils.github_access import (
    invalidate_for_user,
    list_orgs_for_user,
)


async def orgs_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    user = await current_user_for_manager(dialog_manager)
    config: Config = dialog_manager.middleware_data["config"]

    try:
        orgs = await list_orgs_for_user(user, config)
    except Exception as e:
        return {
            "no_auth": False,
            "has_error": True,
            "error": str(e)[:200],
            "orgs": [],
        }

    if not orgs:
        return {
            "no_auth": True,
            "has_error": False,
            "orgs": [],
        }

    return {
        "no_auth": False,
        "has_error": False,
        "orgs": [{**o, "label": org_label(o)} for o in orgs],
    }


async def on_org_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    item_id: str,
) -> None:
    user = await current_user_for_manager(manager)
    config: Config = manager.middleware_data["config"]
    orgs = await list_orgs_for_user(user, config)
    selected = next((o for o in orgs if o["login"] == item_id), None)
    if selected is None:
        await callback.answer("Organisation not found.", show_alert=True)
        return

    state = ReposState.load(manager)
    state.selected_org = selected["login"]
    state.selected_personal = selected["is_personal"]
    state.selected_source = selected["source"]
    state.selected_installation_id = selected["installation_id"]
    state.save(manager)

    await manager.switch_to(ReposSG.repos)


async def on_orgs_refresh(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    user = await current_user_for_manager(manager)
    config: Config = manager.middleware_data["config"]
    if user is not None:
        await invalidate_for_user(user, config)
    await callback.answer("Refreshed.")


orgs_window = Window(
    Const("🏢 <b>Choose where to look</b>"),
    Const(
        "\n❌ You haven't authorized me with GitHub yet.\n"
        "Tap <b>🔌 Connect</b> on the keyboard to install the GitHub App "
        "or set a Personal Access Token.",
        when="no_auth",
    ),
    Format("\n❌ Couldn't fetch organisations: {error}", when="has_error"),
    Const(
        "\n<i>Tag legend: [A] = via GitHub App  •  [P] = via Personal Access Token</i>",
        when="orgs",
    ),
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
