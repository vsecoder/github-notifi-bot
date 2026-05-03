"""member — collaborator added / removed / edited."""
from typing import Optional

from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import repo_link, user_link
from app.events._registry import register


class MemberEvent(_Base):
    action: str  # added | removed | edited
    member: GitHubUser
    repository: Repository
    sender: GitHubUser


def member_message(event: MemberEvent, ctx: EventCtx) -> Optional[str]:
    if event.action != "added":
        return None
    return (
        f"<b>👥 {user_link(event.member)} added as collaborator to "
        f"{repo_link(event.repository)}</b>\n"
        f"By {user_link(event.sender)}"
    )


register("member", MemberEvent, member_message)
