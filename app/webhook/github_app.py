"""FastAPI endpoints for the GitHub App flow.

* ``GET  /github/setup`` — Setup URL callback. GitHub redirects users here
  after they install the App on selected repos. We verify the HMAC ``state``
  parameter (which encodes the Telegram user id), upsert an ``Installation``
  row, and bounce the user back into Telegram.

* ``POST /webhook``      — single App-level webhook endpoint with HMAC
  verification. Handles ``installation`` lifecycle events (deleted /
  suspended / created backfill) and dispatches per-repo events to all
  matching ``Integration`` rows with ``auth_source="app"``.
"""
import logging

import aiohttp
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db.functions import EventSetting, Installation, Integration, User
from app.db.models import AuthSource
from app.events import EventCtx, build_message
from app.utils.github_app import (
    get_account_for_installation,
    get_installation_token,
    verify_state,
    verify_webhook_signature,
)
from app.webhook.api import check_floodwait, config, send_message

router = APIRouter()


# ---------- Setup URL callback ----------

@router.get("/github/setup")
async def setup_callback(
    installation_id: int = Query(...),
    setup_action: str = Query(...),
    state: str | None = Query(None),
):
    if state is None:
        raise HTTPException(
            400,
            "Missing 'state' parameter. Did you start the install through "
            "the bot's /install command?",
        )

    telegram_user_id = verify_state(config, state)
    if telegram_user_id is None:
        raise HTTPException(400, "Invalid state — HMAC mismatch.")

    user = await User.get_or_none(telegram_id=telegram_user_id)
    if user is None:
        await User.register(telegram_user_id)
        user = await User.get(telegram_id=telegram_user_id)

    try:
        account_login = get_account_for_installation(config, installation_id)
    except Exception:
        logging.exception(
            "Couldn't fetch account for installation %s", installation_id
        )
        account_login = "?"

    await Installation.upsert(
        installation_id=installation_id,
        account_login=account_login,
        user_id=user.id,
    )

    logging.info(
        "Recorded installation %s for telegram_user_id=%s, account=%s, action=%s",
        installation_id,
        telegram_user_id,
        account_login,
        setup_action,
    )

    bot_username = config.bot.username
    if bot_username:
        return RedirectResponse(
            f"https://t.me/{bot_username}?start=installed_{installation_id}",
            status_code=302,
        )

    # Fallback if bot_username isn't configured — show a simple confirmation.
    return HTMLResponse(
        "<!doctype html>"
        "<html><body style='font-family: system-ui; padding: 2rem;'>"
        "<h1>✅ App installed</h1>"
        f"<p>Account: <code>{account_login}</code></p>"
        "<p>Open Telegram and return to the bot to continue.</p>"
        "</body></html>"
    )


# ---------- App-level webhook ----------

@router.post("/webhook")
async def app_webhook(
    req: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(
        None, alias="X-Hub-Signature-256"
    ),
):
    body = await req.body()
    if not verify_webhook_signature(config, body, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")

    payload = await req.json()

    # Top-priority: installation lifecycle. Suspending/deleting wipes the
    # row so we don't keep stale entries; ``created`` backfills the account
    # login if the Setup-URL callback couldn't fetch it (race / API hiccup).
    if x_github_event == "installation":
        action = payload.get("action")
        installation_id = payload.get("installation", {}).get("id")
        if installation_id and action in {"deleted", "suspend"}:
            removed = await Installation.delete_by_installation_id(
                installation_id
            )
            logging.info(
                "Installation %s %s — removed %s row(s)",
                installation_id,
                action,
                removed,
            )
            return {"status": "ok", "action": action}

        if installation_id and action == "created":
            account_login = (
                payload.get("installation", {})
                .get("account", {})
                .get("login")
            )
            existing = await Installation.get_by_installation_id(
                installation_id
            )
            if existing is not None and account_login:
                if existing.account_login != account_login:
                    await Installation.filter(id=existing.id).update(
                        account_login=account_login
                    )
                    logging.info(
                        "Backfilled installation %s account_login=%s from webhook payload",
                        installation_id,
                        account_login,
                    )
            return {"status": "ok", "action": action}

        # Other actions (unsuspend, new_permissions_accepted, …) — we
        # already record installations through /github/setup, so just log.
        logging.info(
            "Installation event %s for id=%s (no action taken)",
            action,
            installation_id,
        )
        return {"status": "ok", "action": action}

    # Dispatch per-repo events to App-based integrations.
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {}).get("full_name")
    if not installation_id or not repo:
        logging.info(
            "App webhook %s: missing installation/repo, skipping (payload keys=%s)",
            x_github_event,
            list(payload.keys()),
        )
        return {"status": "ok"}

    integrations = (
        await Integration.filter(
            auth_source=AuthSource.app.value,
            installation__installation_id=installation_id,
            repository_name=repo,
        ).prefetch_related("chat", "user", "installation")
    )

    if not integrations:
        logging.debug(
            "App webhook %s for %s: no matching integrations",
            x_github_event,
            repo,
        )
        return {"status": "ok", "matched": 0}

    # Mint installation token once per request — it's shared across chats
    # for the same installation. Used both for the EventCtx (commit_message
    # uses it for diff stats) and as a fallback for any other formatter.
    try:
        inst_token = get_installation_token(config, installation_id)
    except Exception:
        logging.exception(
            "Couldn't mint installation token for %s", installation_id
        )
        inst_token = None

    sent = 0
    async with aiohttp.ClientSession() as session:
        for integration in integrations:
            chat = integration.chat
            if chat is None:
                continue

            if not await EventSetting.is_enabled(
                chat.chat_id, x_github_event
            ):
                continue
            if x_github_event == "star" and check_floodwait(
                chat.chat_id, chat.floodwait
            ):
                continue

            # ``installation_id`` triggers proper Auth.AppInstallationAuth in
            # formatters; ``auth_token`` stays as a no-op fallback.
            ctx = EventCtx(
                auth_token=inst_token,
                installation_id=installation_id,
                config=config,
            )
            message = build_message(x_github_event, payload, ctx)
            if message:
                await send_message(session, integration, message)
                sent += 1

    return {"status": "ok", "matched": len(integrations), "sent": sent}
