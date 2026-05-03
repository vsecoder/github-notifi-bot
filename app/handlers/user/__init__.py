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
    # DM reply-keyboard taps must beat the dialogs' MessageInput, otherwise
    # tapping "❓ Help" while in TokenSG.awaiting_token would feed "❓ Help"
    # to the token validator. Each handler resets the dialog stack so we
    # don't leave dangling dialog state.
    router.include_router(dm_menu.router)
    # Dialog windows: MessageInput state filters take precedence over the
    # catch-all text handler below.
    router.include_router(get_dialogs_router())
    router.include_router(start.router)
    router.include_router(token.router)
    # Catch-all DM text handler comes last.
    router.include_router(text.router)

    return router
