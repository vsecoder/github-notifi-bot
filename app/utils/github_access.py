"""Read-only abstraction over PyGithub for listing orgs / repos.

Two auth sources are supported in parallel:

* **PAT** — the classic per-user Personal Access Token path.
* **App** — short-lived installation tokens minted from a GitHub App.

UI dialogs call ``list_orgs_for_user`` / ``list_repos_for_org`` and don't
care which source the data came from. ``OrgSummary.source`` carries the
routing tag so callers (e.g. ``integrate_repo``) can pick the right
integration code path.
"""
import asyncio
import time
from typing import TypedDict

from github import Auth, Github, GithubException

from app.config import Config


class OrgSummary(TypedDict):
    login: str
    is_personal: bool
    source: str  # "pat" | "app"
    installation_id: int  # 0 for PAT, real id for App


class RepoSummary(TypedDict):
    full_name: str
    name: str
    owner: str
    private: bool
    stars: int
    description: str
    permissions_admin: bool
    source: str  # "pat" | "app"
    installation_id: int  # 0 for PAT


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
    """Drop all cache entries owned by this PAT."""
    for key in [k for k in _cache if k and k[0] == token]:
        _cache.pop(key, None)


def invalidate_installation(installation_id: int) -> None:
    """Drop all cache entries owned by this installation."""
    tag = f"app:{installation_id}"
    for key in [k for k in _cache if k and k[0] == tag]:
        _cache.pop(key, None)


def _gh(token: str) -> Github:
    return Github(auth=Auth.Token(token))


# ---------- PAT-source ----------

def _list_orgs_pat_sync(token: str) -> list[OrgSummary]:
    g = _gh(token)
    me = g.get_user()
    orgs: list[OrgSummary] = [
        OrgSummary(
            login=me.login, is_personal=True, source="pat", installation_id=0
        )
    ]
    try:
        for org in me.get_orgs():
            orgs.append(
                OrgSummary(
                    login=org.login,
                    is_personal=False,
                    source="pat",
                    installation_id=0,
                )
            )
    except GithubException:
        pass
    return orgs


def _list_repos_pat_sync(
    token: str, org_login: str, is_personal: bool
) -> list[RepoSummary]:
    g = _gh(token)
    if is_personal:
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
                source="pat",
                installation_id=0,
            )
        )
    result.sort(
        key=lambda x: (not x["permissions_admin"], -x["stars"], x["full_name"])
    )
    return result


# ---------- App-source ----------

def _gh_for_installation(config: Config, installation_id: int) -> Github:
    # Local import to avoid a circular dependency between hooks and github_app.
    from app.utils.github_app import get_installation_token

    token = get_installation_token(config, installation_id)
    return Github(auth=Auth.Token(token))


def _list_repos_via_installation_sync(
    config: Config, installation_id: int
) -> list[RepoSummary]:
    g = _gh_for_installation(config, installation_id)
    requester = getattr(g, "requester", None) or getattr(
        g, "_Github__requester", None
    )
    if requester is None:
        return []

    all_repos: list[RepoSummary] = []
    page = 1
    # Cap pagination defensively — installations rarely cover >1000 repos
    # and we'd rather lose the tail than spin on misbehaving APIs.
    while page <= 10:
        try:
            _, body = requester.requestJsonAndCheck(
                "GET",
                f"/installation/repositories?per_page=100&page={page}",
            )
        except Exception:
            break
        if not isinstance(body, dict):
            break
        page_repos = body.get("repositories") or []
        if not page_repos:
            break
        for r in page_repos:
            owner = (r.get("owner") or {}).get("login") or ""
            all_repos.append(
                RepoSummary(
                    full_name=r.get("full_name") or "",
                    name=r.get("name") or "",
                    owner=owner,
                    private=bool(r.get("private", False)),
                    stars=int(r.get("stargazers_count") or 0),
                    description=(r.get("description") or "")[:200],
                    # For App-source, the App itself owns the right to install
                    # a webhook, so we always show "can integrate" — no admin
                    # check on the user's side is needed.
                    permissions_admin=True,
                    source="app",
                    installation_id=installation_id,
                )
            )
        if len(page_repos) < 100:
            break
        page += 1

    all_repos.sort(key=lambda x: (-x["stars"], x["full_name"]))
    return all_repos


# ---------- Public resolvers (UI calls these) ----------

async def list_orgs_for_user(
    user, config: Config
) -> list[OrgSummary]:
    """Merged list of orgs/accounts the user can browse, deduped by login.
    Includes:
      * PAT-source: personal namespace + organisations visible via the token
      * App-source: each installation the user owns

    If both sources cover the same login, keeps the App entry — App scopes
    are explicit and usually narrower / more current.
    """
    # Local import — User and Installation live in db.functions which
    # imports from this module's neighbour modules; deferring keeps the
    # dependency graph clean.
    from app.db.functions import Installation

    seen: set[str] = set()
    result: list[OrgSummary] = []

    # App first (preferred for dedup).
    if config.github_app.is_configured and user is not None:
        installations = await Installation.for_user(user.id)
        for inst in installations:
            login = inst.account_login
            if not login or login in seen:
                continue
            seen.add(login)
            result.append(
                OrgSummary(
                    login=login,
                    is_personal=False,
                    source="app",
                    installation_id=inst.installation_id,
                )
            )

    # PAT fallback.
    if user is not None and user.token:
        token = user.token
        key = (token, "orgs")
        cached = _get(key)
        if cached is None:
            try:
                cached = await asyncio.to_thread(_list_orgs_pat_sync, token)
            except Exception:
                cached = []
            _set(key, cached)
        for org in cached:  # type: ignore[union-attr]
            if org["login"] in seen:
                continue
            seen.add(org["login"])
            result.append(org)

    return result


async def list_repos_for_org(
    user, org: OrgSummary, config: Config
) -> list[RepoSummary]:
    """Repos for the chosen org, routed by ``org["source"]``."""
    if org["source"] == "app":
        installation_id = org["installation_id"]
        key = (f"app:{installation_id}", "repos")
        cached = _get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = await asyncio.to_thread(
            _list_repos_via_installation_sync, config, installation_id
        )
        _set(key, result)
        return result

    # PAT
    if user is None or not user.token:
        return []
    key = (user.token, "repos", org["login"], org["is_personal"])
    cached = _get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    result = await asyncio.to_thread(
        _list_repos_pat_sync, user.token, org["login"], org["is_personal"]
    )
    _set(key, result)
    return result


async def list_repos_for_installation(
    config: Config, installation_id: int
) -> list[RepoSummary]:
    """Direct App-source listing — used by ``integrate_repo`` to verify
    the App still has access to the chosen repo."""
    key = (f"app:{installation_id}", "repos")
    cached = _get(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    result = await asyncio.to_thread(
        _list_repos_via_installation_sync, config, installation_id
    )
    _set(key, result)
    return result


async def invalidate_for_user(user, config: Config) -> None:
    """Drop all cache entries belonging to this user — both PAT cache
    (if they have a token) and every installation they own."""
    from app.db.functions import Installation

    if user is not None and user.token:
        invalidate(user.token)
    if user is not None:
        installations = await Installation.for_user(user.id)
        for inst in installations:
            invalidate_installation(inst.installation_id)
