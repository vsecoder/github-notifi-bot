"""Aiogram-dialog flows. Each dialog is a Router-subclass; this module
exposes a single helper that bundles all of them for the dispatcher tree."""
from aiogram import Router

from app.dialogs.token import token_dialog


def get_dialogs_router() -> Router:
    router = Router()
    router.include_router(token_dialog)
    return router


__all__ = ["get_dialogs_router", "token_dialog"]
