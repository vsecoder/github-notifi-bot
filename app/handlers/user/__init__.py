from aiogram import Router


def get_user_router() -> Router:
    from . import integration, start, token, text, event_settings

    router = Router()
    router.include_router(integration.router)
    router.include_router(event_settings.router)
    router.include_router(start.router)
    router.include_router(token.router)
    router.include_router(text.router)

    return router
