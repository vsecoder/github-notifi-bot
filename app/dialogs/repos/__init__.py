"""Repos browser dialog package.

Five windows on a single ``ReposSG``, split across modules for readability:

* ``orgs``                — orgs accessible by the user (PAT + App merged).
* ``repos``               — paginated repo list for the selected org.
* ``repo_detail``         — info about one repo + Integrate button.
* ``choose_chat``         — list of admin chats; picking one performs the
                            integration directly.
* ``integration_result``  — success / failure feedback.
"""
from aiogram_dialog import Dialog

from app.dialogs.repos._choose_chat_window import choose_chat_window
from app.dialogs.repos._detail_window import repo_detail_window
from app.dialogs.repos._orgs_window import orgs_window
from app.dialogs.repos._repos_window import repos_window
from app.dialogs.repos._result_window import integration_result_window
from app.dialogs.repos.state import ReposSG, ReposState


repos_dialog = Dialog(
    orgs_window,
    repos_window,
    repo_detail_window,
    choose_chat_window,
    integration_result_window,
)


__all__ = ["ReposSG", "ReposState", "repos_dialog"]
