"""push — commits pushed to a branch.

File lists (added / removed / modified) come straight out of the webhook
payload — no API call needed. The line-count diff (`+N / -N`) does need an
API hit per commit, so we treat it as optional enrichment when the user
token is available and the call doesn't fail.
"""
import logging
from typing import Optional

from github import Auth, Github

from app.events._base import _Base, GitHubUser, Repository
from app.events._context import EventCtx
from app.events._formatting import _ as _e
from app.events._registry import register


class CommitAuthor(_Base):
    name: str
    email: Optional[str] = None
    username: Optional[str] = None


class Commit(_Base):
    id: str
    message: str
    url: str
    author: CommitAuthor
    # GitHub includes these arrays directly in the push payload — see
    # https://docs.github.com/en/webhooks/webhook-events-and-payloads#push
    added: list[str] = []
    removed: list[str] = []
    modified: list[str] = []


class PushEvent(_Base):
    ref: str
    compare: str
    commits: list[Commit] = []
    repository: Repository
    sender: GitHubUser


def commit_message(event: PushEvent, ctx: EventCtx) -> str:
    branch = event.ref.split("/")[-1]
    repo_link_str = (
        f'<a href="{event.repository.html_url}">'
        f"{_e(event.repository.full_name)}:{_e(branch)}</a>"
    )

    if not event.commits:
        return f"<b>📏 On {repo_link_str} new empty push</b>"

    # Only used to pull `+/-` line counts, which aren't in the webhook payload.
    # File lists themselves come from the payload — no API call required.
    repo_api = None
    if ctx.user_token:
        try:
            repo_api = Github(auth=Auth.Token(ctx.user_token)).get_repo(
                event.repository.full_name
            )
        except Exception as e:
            logging.warning(
                "Couldn't open repo %s for line-stat enrichment: %s",
                event.repository.full_name,
                e,
            )

    blocks = []
    for c in event.commits:
        author_name = _e(c.author.name)
        if c.author.username:
            author_link = (
                f'<a href="https://github.com/{_e(c.author.username)}">'
                f"@{_e(c.author.username)}</a>"
            )
        else:
            author_link = f"<i>{author_name}</i>"

        block = (
            f'<blockquote expandable="expandable"><b>Commit '
            f'<a href="{c.url}">#{c.id[:7]}</a> by '
            f"<i>{author_name} ({author_link})</i></b>\n"
            f"<i>{_e(c.message)}</i>\n"
        )

        # File lists straight from payload.
        if c.added:
            block += (
                f"\n<b>🔧 Created files:</b>\n"
                f"<code>{_e(chr(10).join(c.added))}</code>\n"
            )
        if c.removed:
            block += (
                f"\n<b>🗑 Removed files:</b>\n"
                f"<code>{_e(chr(10).join(c.removed))}</code>\n"
            )
        if c.modified:
            block += (
                f"\n<b>🖊 Modified files:</b>\n"
                f"<code>{_e(chr(10).join(c.modified))}</code>\n"
            )

        # Line counts via API — best-effort enrichment.
        if repo_api is not None:
            try:
                detail = repo_api.get_commit(c.id)
                add_lines = sum(f.additions for f in detail.files)
                del_lines = sum(f.deletions for f in detail.files)
                if add_lines or del_lines:
                    block += (
                        f"\n<b>⌨️ Diff:</b>\n"
                        f"➕ {add_lines}\n➖ {del_lines}\n"
                    )
            except Exception as e:
                logging.warning(
                    "Couldn't fetch line counts for commit %s: %s",
                    c.id[:7],
                    e,
                )

        block += "</blockquote>"
        blocks.append(block)

    header = (
        f"<b>📏 On {repo_link_str} new commits!</b>\n"
        f"{len(event.commits)} commits pushed.\n"
        f'<a href="{event.compare}">Compare changes</a>\n\n'
    )
    return header + "\n".join(blocks)


register("push", PushEvent, commit_message)
