from aiogram import Router


def get_user_router() -> Router:
    from app.dialogs import get_dialogs_router

    from . import (
        dm_menu,
        event_settings,
        integration,
        reinstall,
        start,
        text,
        token,
    )

    router = Router()
    # Group / shared commands first.
    router.include_router(integration.router)
    router.include_router(reinstall.router)
    router.include_router(event_settings.router)
    # Dialog windows must be reachable before the catch-all text handler so
    # that MessageInput state filters get to match before text.router does.
    router.include_router(get_dialogs_router())
    # DM-only reply-keyboard taps (filtered by F.chat.type == "private").
    router.include_router(dm_menu.router)
    router.include_router(start.router)
    router.include_router(token.router)
    # Catch-all DM text handler comes last.
    router.include_router(text.router)

    return router
