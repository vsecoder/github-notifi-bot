from fastapi import FastAPI

import uvicorn

from app.webhook.api import router as pat_router
from app.webhook.github_app import router as github_app_router


def dispatcher():
    app = FastAPI()
    # Per-integration PAT webhooks: POST /webhook/{integration_token}
    app.include_router(router=pat_router, prefix="/webhook")
    # GitHub App: GET /github/setup + POST /webhook (App-level, single URL)
    app.include_router(router=github_app_router)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    uvicorn.run(app, host="0.0.0.0", port=4454)
