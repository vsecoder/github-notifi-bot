from typing import Optional

from app.db import models
import string
import random


class User(models.User):
    @classmethod
    async def is_registered(cls, telegram_id: int) -> Optional["User"]:
        return await cls.get_or_none(telegram_id=telegram_id)

    @classmethod
    async def register(cls, telegram_id):
        await User(telegram_id=telegram_id).save()

    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def write_token(cls, telegram_id: int, token: str):
        await cls.filter(telegram_id=telegram_id).update(token=token)

    @classmethod
    async def get_by_id(cls, id: int) -> Optional["User"]:
        return await cls.get_or_none(id=id)


class Chat(models.Chat):
    @classmethod
    async def is_registered(cls, chat_id: int) -> Optional["Chat"]:
        return await cls.get_or_none(chat_id=chat_id)

    @classmethod
    async def ensure_registered(cls, chat_id: int) -> "Chat":
        chat = await cls.get_or_none(chat_id=chat_id)
        if chat is None:
            chat = await cls.create(chat_id=chat_id)
        await EventSetting.init_for_chat(chat_id)
        return chat

    @classmethod
    async def get_chat(cls, chat_id: int) -> Optional["Chat"]:
        return await cls.get_or_none(chat_id=chat_id)

    @classmethod
    async def register(cls, chat_id: int):
        await cls.create(chat_id=chat_id)

    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_integrations(cls, chat_id: int) -> list:
        chat = await cls.get_or_none(chat_id=chat_id)
        if chat is None:
            return []
        return await chat.integrations.all()  # type: ignore[attr-defined]

    @classmethod
    async def add_integration(cls, chat_id: int, user_id: int, repository_name: str) -> tuple:
        chat = await cls.get(chat_id=chat_id)
        user = await User.get(id=user_id)

        existing = await Integration.filter(
            repository_name=repository_name, user=user
        ).first()

        if existing:
            integration = await Integration.create(
                chat=chat,
                user=user,
                repository_name=repository_name,
                integration_token=existing.integration_token,
            )
            return integration, True

        integration_token = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=16)
        )
        integration = await Integration.create(
            chat=chat,
            user=user,
            repository_name=repository_name,
            integration_token=integration_token,
        )
        return integration, False

    @classmethod
    async def remove_integration(cls, chat_id: int, integration_id: int):
        await Integration.filter(chat_id=chat_id, id=integration_id).delete()

    @classmethod
    async def get_topic(cls, chat_id: int) -> Optional[int]:
        chat = await cls.get_or_none(chat_id=chat_id)
        return chat.topic_id if chat else None

    @classmethod
    async def set_topic(cls, chat_id: int, topic_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=topic_id)

    @classmethod
    async def remove_topic(cls, chat_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=None)

    @classmethod
    async def get_by_integration(cls, integration_id: int) -> Optional["Chat"]:
        integration = await Integration.get_or_none(id=integration_id).prefetch_related(
            "chat"
        )
        return integration.chat if integration else None


class Integration(models.Integration):
    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_by_id(cls, integration_id: int) -> Optional["Integration"]:
        return await cls.get_or_none(id=integration_id)

    @classmethod
    async def get_by_repo(cls, repository_name: str) -> list:
        return await cls.filter(repository_name=repository_name).all()

    @classmethod
    async def get_by_chat_and_repo(
        cls, chat_id: int, repo_name: str
    ) -> Optional["Integration"]:
        chat = await Chat.get_or_none(chat_id=chat_id)
        if chat is None:
            return None
        return await cls.get_or_none(chat=chat, repository_name=repo_name)

    @classmethod
    async def create_integration(
        cls,
        repository_name: str,
        chat_id: int,
        user_id: int,
        integration_token: Optional[str] = None,
    ):
        chat = await Chat.get(chat_id=chat_id)
        user = await User.get(id=user_id)
        if integration_token is None:
            integration_token = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=16)
            )

        return await cls.create(
            repository_name=repository_name,
            chat=chat,
            user=user,
            integration_token=integration_token,
        )

    @classmethod
    async def update_last_commit(cls, integration_id: int, commit: str):
        await cls.filter(id=integration_id).update(last_commit=commit)

    @classmethod
    async def delete_by_id(cls, integration_id: int):
        await cls.filter(id=integration_id).delete()

    @classmethod
    async def get_by_token(cls, token: str) -> list:
        return (
            await cls.filter(integration_token=token)
            .prefetch_related("chat", "user")
            .all()
        )


class Installation(models.Installation):
    @classmethod
    async def upsert(
        cls, installation_id: int, account_login: str, user_id: int
    ) -> "Installation":
        """Create or update the installation row. Same Telegram user
        re-installing on the same GitHub account just refreshes the row."""
        existing = await cls.get_or_none(installation_id=installation_id)
        if existing is not None:
            await cls.filter(id=existing.id).update(
                account_login=account_login,
                user_id=user_id,
            )
            return await cls.get(installation_id=installation_id)
        return await cls.create(
            installation_id=installation_id,
            account_login=account_login,
            user_id=user_id,
        )

    @classmethod
    async def for_user(cls, user_id: int) -> list["Installation"]:
        return list(await cls.filter(user_id=user_id))

    @classmethod
    async def get_by_installation_id(
        cls, installation_id: int
    ) -> Optional["Installation"]:
        return await cls.get_or_none(installation_id=installation_id)

    @classmethod
    async def delete_by_installation_id(cls, installation_id: int) -> int:
        """Returns the number of rows deleted (0 if not found)."""
        return await cls.filter(installation_id=installation_id).delete()


class EventSetting(models.Eventsetting):
    @classmethod
    async def init_for_chat(cls, chat_id: int) -> None:
        for event_type in models.EventType:
            await cls.get_or_create(
                defaults={"enabled": True},
                chat_id=chat_id,
                event_type=event_type.value,
            )

    @classmethod
    async def enable(cls, chat_id: int, event_type: models.EventType) -> None:
        await cls.update_or_create(
            defaults={"enabled": True},
            chat_id=chat_id,
            event_type=event_type.value,
        )

    @classmethod
    async def disable(cls, chat_id: int, event_type: models.EventType) -> None:
        await cls.update_or_create(
            defaults={"enabled": False},
            chat_id=chat_id,
            event_type=event_type.value,
        )

    @classmethod
    async def is_enabled(cls, chat_id: int, event_type: str) -> bool:
        setting = await cls.get_or_none(chat_id=chat_id, event_type=event_type)
        return setting.enabled if setting else True

    @classmethod
    async def for_chat(cls, chat_id: int) -> "list[EventSetting]":
        return list(await cls.filter(chat_id=chat_id))
