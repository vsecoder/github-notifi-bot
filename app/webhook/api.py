from fastapi import APIRouter, Request
from app.db.functions import Chat, Integration

from app.config import parse_config

import requests

router = APIRouter()
config = parse_config()


@router.post("/")
async def webhook(req: Request, code: str):
    """
    Endpoint that receives the webhook payload.
    This endpoint is called by Github when the webhook is triggered.
    The payload is passed as a query parameters.
    """
    res = await req.json()
    integration = await Integration.get_by_code(code)
    if not integration:
        return {"message": "Integration not found!"}

    chat = await Chat.get_by_id(integration.chat_id)

    modified = "\n".join([file for file in res["head_commit"]["modified"]])

    message = f"""<b>📏 {res["repository"]["full_name"]} new commit!</b>
<i>{res["head_commit"]["message"]}</i>
<a href="{res["compare"]}">#{res["head_commit"]["id"][:7]}</a> by <i>{res["head_commit"]["author"]["name"]} (@{res["head_commit"]["author"]["username"]})</i>

<b>🖊 Modified files:</b>
<code>{modified}</code>
    """

    requests.post(
        f"https://api.telegram.org/bot{config.bot_token}/sendMessage",
        json={
            "chat_id": chat.chat_id,
            "text": message,
            "parse_mode": "HTML",
        },
    )
    return {"message": "Webhook triggered!"}
