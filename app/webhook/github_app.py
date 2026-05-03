"""FastAPI endpoints for the GitHub App flow.

* ``GET  /github/setup`` — Setup URL callback. GitHub redirects users here
  after they install the App on selected repos. We verify the HMAC ``state``
  parameter (which encodes the Telegram user id), upsert an ``Installation``
  row, and bounce the user back into Telegram.

* ``POST /webhook``      — single App-level webhook endpoint with HMAC
  verification. For now: handles ``installation`` lifecycle events (deleted,
  suspended) and logs everything else. Per-event delivery to chats lands
  in PR 6 once App-based ``Integration`` rows can exist.
"""
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db.functions import Installation, User
from app.utils.github_app import (
    get_account_for_installation,
    verify_state,
    verify_webhook_signature,
)
from app.webhook.api import config

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

    # Per-repo events for App-based integrations are dispatched in PR 6.
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {}).get("full_name")
    logging.info(
        "App webhook received: event=%s installation_id=%s repo=%s",
        x_github_event,
        installation_id,
        repo,
    )

    return {"status": "ok"}
