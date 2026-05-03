"""``ReposSG`` state group + Pydantic ``ReposState`` mirror over dialog_data."""
from typing import Optional

from aiogram.fsm.state import State, StatesGroup

from app.utils.dialog_state import DialogState
from app.utils.github_access import OrgSummary


class ReposSG(StatesGroup):
    orgs = State()
    repos = State()
    repo_detail = State()
    choose_chat = State()
    integration_result = State()


class ReposState(DialogState):
    """Typed view over ReposSG.dialog_data."""
    selected_org: Optional[str] = None
    selected_personal: bool = False
    selected_source: str = "pat"
    selected_installation_id: int = 0
    selected_repo: Optional[str] = None
    result_success: bool = False
    result_message: Optional[str] = None

    def selected_org_summary(self) -> Optional[OrgSummary]:
        if not self.selected_org:
            return None
        return OrgSummary(
            login=self.selected_org,
            is_personal=self.selected_personal,
            source=self.selected_source,
            installation_id=self.selected_installation_id,
        )
