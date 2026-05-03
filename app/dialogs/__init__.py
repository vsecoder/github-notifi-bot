"""Aiogram-dialog flows. Each dialog is a Router-subclass; this module
exposes a single helper that bundles all of them for the dispatcher tree."""
from aiogram import Router

from app.dialogs.my_chats import my_chats_dialog
from app.dialogs.repos import repos_dialog
from app.dialogs.token import token_dialog


def get_dialogs_router() -> Router:
    router = Router()
    router.include_router(token_dialog)
    router.include_router(repos_dialog)
    router.include_router(my_chats_dialog)
    return router


__all__ = [
    "get_dialogs_router",
    "my_chats_dialog",
    "repos_dialog",
    "token_dialog",
]
