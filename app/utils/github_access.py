"""Read-only abstraction over PyGithub for listing orgs / repos.

This module is the seam between UI dialogs and the authentication mechanism:
today everything goes through the user's PAT. When the GitHub App migration
lands, swap the implementations behind ``list_orgs`` / ``list_repos`` to use
installation tokens — the dialogs themselves don't need to change.

Results are cached in-process for ``_TTL`` seconds. Call :func:`invalidate`
to drop a user's cache entries (e.g. on a Refresh button).
"""
import asyncio
import time
from typing import TypedDict

from github import Auth, Github, GithubException


class OrgSummary(TypedDict):
    login: str
    is_personal: bool


class RepoSummary(TypedDict):
    full_name: str
    name: str
    owner: str
    private: bool
    stars: int
    description: str
    permissions_admin: bool


_TTL = 300.0  # 5 minutes
_cache: dict[tuple, tuple[object, float]] = {}


def _get(key: tuple) -> object | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if expires_at <= time.monotonic():
        _cache.pop(key, None)
        return None
    return value


def _set(key: tuple, value: object) -> None:
    _cache[key] = (value, time.monotonic() + _TTL)


def invalidate(token: str) -> None:
    """Drop all cache entries owned by this token."""
    for key in [k for k in _cache if k and k[0] == token]:
        _cache.pop(key, None)


def _gh(token: str) -> Github:
    return Github(auth=Auth.Token(token))


# ---------- orgs ----------

def _list_orgs_sync(token: str) -> list[OrgSummary]:
    g = _gh(token)
    me = g.get_user()
    orgs: list[OrgSummary] = [
        OrgSummary(login=me.login, is_personal=True)
    ]
    try:
        for org in me.get_orgs():
            orgs.append(OrgSummary(login=org.login, is_personal=False))
    except GithubException:
        pass
    return orgs


async def list_orgs(token: str) -> list[OrgSummary]:
    key = (token, "orgs")
    cached = _get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    result = await asyncio.to_thread(_list_orgs_sync, token)
    _set(key, result)
    return result


# ---------- repos ----------

def _list_repos_sync(
    token: str, org_login: str, is_personal: bool
) -> list[RepoSummary]:
    g = _gh(token)
    if is_personal:
        # PyGithub stubs miss `affiliation` on AuthenticatedUser.get_repos;
        # we pass via **kwargs to dodge the type-check while keeping the
        # API call correct (filters out org-member repos so the personal
        # list doesn't duplicate the per-org listing).
        kw: dict[str, str] = {"affiliation": "owner,collaborator"}
        repos_iter = g.get_user().get_repos(**kw)
    else:
        repos_iter = g.get_organization(org_login).get_repos()

    result: list[RepoSummary] = []
    for r in repos_iter:
        try:
            perms = r.permissions
            admin = bool(perms and perms.admin)
        except Exception:
            admin = False
        result.append(
            RepoSummary(
                full_name=r.full_name,
                name=r.name,
                owner=r.owner.login,
                private=r.private,
                stars=r.stargazers_count,
                description=(r.description or "")[:200],
                permissions_admin=admin,
            )
        )
    result.sort(key=lambda x: (not x["permissions_admin"], -x["stars"], x["full_name"]))
    return result


async def list_repos(
    token: str, org_login: str, is_personal: bool
) -> list[RepoSummary]:
    key = (token, "repos", org_login, is_personal)
    cached = _get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    result = await asyncio.to_thread(
        _list_repos_sync, token, org_login, is_personal
    )
    _set(key, result)
    return result
