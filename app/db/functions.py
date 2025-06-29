from typing import Union

from tortoise.exceptions import DoesNotExist

from app.db import models
import string
import random


class User(models.User):
    @classmethod
    async def is_registered(cls, telegram_id: int) -> Union[models.User, bool]:
        try:
            return await cls.get(telegram_id=telegram_id)
        except DoesNotExist:
            return False

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
    async def get_by_id(cls, id: int) -> Union[models.User, bool]:
        try:
            return await cls.get(id=id)
        except DoesNotExist:
            return False


class Chat(models.Chat):
    @classmethod
    async def is_registered(cls, chat_id: int) -> Union[models.Chat, bool]:
        try:
            return await cls.get(chat_id=chat_id)
        except DoesNotExist:
            return False

    @classmethod
    async def ensure_registered(cls, chat_id: int):
        if not await cls.is_registered(chat_id):
            await cls.create(chat_id=chat_id)

    @classmethod
    async def get_chat(cls, chat_id: int) -> Union[models.Chat, bool]:
        try:
            return await cls.get(chat_id=chat_id)
        except DoesNotExist:
            return False

    @classmethod
    async def register(cls, chat_id: int):
        await cls.create(chat_id=chat_id)

    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_integrations(cls, chat_id: int) -> list:
        chat = await cls.get(chat_id=chat_id).prefetch_related("integrations")
        return await chat.integrations.all()

    @classmethod
    async def add_integration(cls, chat_id: int, user_id: int, repository_name: str) -> tuple:
        chat = await cls.get(chat_id=chat_id)
        user = await User.get(id=user_id)

        existing = await Integration.filter(
            repository_name=repository_name, user=user
        ).first()

        if existing:
            integration_token = existing.integration_token
        else:
            integration_token = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=16)
            )

        return (
            await Integration.create(
                chat=chat,
                user=user,
                repository_name=repository_name,
                integration_token=integration_token,
            ),
            existing,
        )

    @classmethod
    async def remove_integration(cls, chat_id: int, integration_id: int):
        await Integration.filter(chat_id=chat_id, id=integration_id).delete()

    @classmethod
    async def get_topic(cls, chat_id: int) -> Union[int, bool]:
        try:
            chat = await cls.get(chat_id=chat_id)
            return chat.topic_id
        except DoesNotExist:
            return False

    @classmethod
    async def set_topic(cls, chat_id: int, topic_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=topic_id)

    @classmethod
    async def remove_topic(cls, chat_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=None)

    @classmethod
    async def get_by_integration(cls, integration_id: int) -> Union[models.Chat, None]:
        integration = await Integration.get(id=integration_id).prefetch_related(
            "chat"
        )
        return integration.chat


class Integration(models.Integration):
    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_by_id(cls, integration_id: int) -> Union[models.Integration, None]:
        try:
            return await cls.get(id=integration_id)
        except DoesNotExist:
            return None

    @classmethod
    async def get_by_repo(cls, repository_name: str) -> list:
        return await cls.filter(repository_name=repository_name).all()

    @classmethod
    async def get_by_chat_and_repo(
        cls, chat_id: int, repo_name: str
    ) -> Union[models.Integration, None]:
        try:
            chat = await Chat.get(chat_id=chat_id)
            return await cls.get(chat=chat, repository_name=repo_name)
        except DoesNotExist:
            return None

    @classmethod
    async def create_integration(
        cls,
        repository_name: str,
        chat_id: int,
        user_id: int,
        integration_token: str = None,
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
    async def delete(cls, integration_id: int):
        await cls.filter(id=integration_id).delete()

    @classmethod
    async def get_by_token(cls, token: str) -> list:
        return (
            await cls.filter(integration_token=token)
            .prefetch_related("chat", "user")
            .all()
        )


class EventSetting(models.Model):
    @classmethod
    async def init_for_chat(cls, chat_id: int) -> list["EventSetting"]:
        for event_type in models.EventType:
            setting, created = await cls.get_or_create(
                chat_id=chat_id, event_type=event_type
            )
            if created:
                setting.enabled = True
                await setting.save()

    @classmethod
    async def enable(cls, chat_id: int, event_type: models.EventType) -> None:
        await cls.update_or_create(
            defaults={"enabled": True}, chat_id=chat_id, event_type=event_type
        )

    @classmethod
    async def disable(cls, chat_id: int, event_type: models.EventType) -> None:
        await cls.update_or_create(
            defaults={"enabled": False}, chat_id=chat_id, event_type=event_type
        )

    @classmethod
    async def is_enabled(cls, chat: Chat, event_type: models.EventType) -> bool:
        # setting = await cls.get_or_none(chat=chat, event_type=event_type)
        setting = await cls.filter(event_type=event_type).prefetch_related("chat")
        setting = [s for s in setting if s.chat == chat]
        return setting[0].enabled if setting else False

    @classmethod
    async def exists(cls, chat: Chat) -> bool:
        settings = await cls.all().prefetch_related("chat")
        settings = [s for s in settings if s.chat == chat]
        return settings
