"""``ReposSG.integration_result`` window — feedback after integration attempt."""
from typing import Any

from aiogram_dialog import DialogManager, Window
from aiogram_dialog.widgets.kbd import Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from app.dialogs.repos.state import ReposSG, ReposState


async def integration_result_getter(
    dialog_manager: DialogManager, **_: Any
) -> dict[str, Any]:
    state = ReposState.load(dialog_manager)
    return {
        "success": state.result_success,
        "fail": not state.result_success,
        "message": state.result_message or "—",
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
