"""release — release published / edited / deleted."""
from typing import Optional

from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e, repo_link, truncate, user_link
from app.events._registry import register


class Release(_Base):
    name: Optional[str] = None
    tag_name: str
    html_url: str
    body: Optional[str] = None
    prerelease: bool = False
    draft: bool = False
    author: GitHubUser


class ReleaseEvent(_Base):
    action: str
    release: Release
    repository: Repository
    sender: GitHubUser


def release_message(event: ReleaseEvent, ctx: EventCtx) -> Optional[str]:
    if event.action != "published":
        return None
    if event.release.draft:
        return None

    title = event.release.name or event.release.tag_name
    pre = " <i>(prerelease)</i>" if event.release.prerelease else ""
    notes = truncate(event.release.body, 500)
    notes_block = (
        f'<blockquote expandable="expandable">{_e(notes)}</blockquote>\n'
        if notes else ""
    )
    return (
        f"<b>🚀 New release on {repo_link(event.repository)}{pre}</b>\n"
        f'<a href="{event.release.html_url}"><b>{_e(event.release.tag_name)}</b></a> — '
        f"<i>{_e(title)}</i>\n"
        f"By {user_link(event.release.author)}\n"
        f"{notes_block}"
    )


register("release", ReleaseEvent, release_message)
