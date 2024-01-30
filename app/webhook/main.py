from fastapi import FastAPI
from app.webhook.api import router as handlers_router

import uvicorn


def dispatcher():
    app = FastAPI()
    app.include_router(router=handlers_router, prefix="/webhook")

    @app.get("/")
    async def root():
        return {
            "message": "Hello World",
        }

    uvicorn.run(app, host="0.0.0.0", port=4454)

    # return app
