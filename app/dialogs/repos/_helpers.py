"""Shared bits used by the per-window modules in this package."""
from aiogram_dialog import DialogManager

from app.db.functions import Integration
from app.utils.dialog_helpers import current_user_for_manager
from app.utils.github_access import OrgSummary, RepoSummary


async def user_integrations(manager: DialogManager) -> set[str]:
    """Set of repository_name's the current user has integrated anywhere."""
    user = await current_user_for_manager(manager)
    if user is None:
        return set()
    rows = await Integration.filter(user_id=user.id).all()
    return {r.repository_name for r in rows if r.repository_name}


def org_label(org: OrgSummary) -> str:
    icon = "👤" if org["is_personal"] else "🏢"
    tag = " " + ("[A]" if org["source"] == "app" else "[P]")
    return f"{icon} {org['login']}{tag}"


def repo_label(repo: RepoSummary, integrated: set[str]) -> str:
    integ = "✅ " if repo["full_name"] in integrated else ""
    private = "🔒" if repo["private"] else "🔓"
    admin = "" if repo["permissions_admin"] else "⚠️ "
    return f"{integ}{admin}{private} {repo['name']}"
