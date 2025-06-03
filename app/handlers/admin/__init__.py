from aiogram import Router


def get_admin_router() -> Router:
    from . import error, mailing

    router = Router()
    router.include_router(error.router)
    router.include_router(mailing.router)

    return router
