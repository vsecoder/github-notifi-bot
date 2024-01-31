from typing import Union

from tortoise.exceptions import DoesNotExist

from app.db import models
import string, random


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


class Chat(models.Chat):
    @classmethod
    async def is_registered(cls, chat_id: int) -> Union[models.Chat, bool]:
        try:
            return await cls.get(chat_id=chat_id)
        except DoesNotExist:
            return False

    @classmethod
    async def get_chat(cls, chat_id: int) -> Union[models.Chat, bool]:
        try:
            return await cls.get(chat_id=chat_id)
        except DoesNotExist:
            return False

    @classmethod
    async def register(cls, chat_id: int):
        await Chat(chat_id=chat_id).save()

    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_integrations(cls, chat_id: int) -> list:
        chat = await cls.get(chat_id=chat_id)
        return chat.integrations

    @classmethod
    async def add_integration(cls, chat_id: int, integration_id: int, user_id: int):
        chat = await cls.get(chat_id=chat_id)
        integrations = chat.integrations
        integrations.append({"integration_id": integration_id, "user_id": user_id})
        await cls.filter(chat_id=chat_id).update(integrations=integrations)

    @classmethod
    async def remove_integration(cls, chat_id: int, integration_id: int):
        chat = await cls.get(chat_id=chat_id)
        integrations = chat.integrations
        integrations = [
            i for i in integrations if i["integration_id"] != integration_id
        ]
        await cls.filter(chat_id=chat_id).update(integrations=integrations)

    @classmethod
    async def get_topic(cls, chat_id: int) -> Union[models.Chat, bool]:
        try:
            return await cls.get(chat_id=chat_id)
        except DoesNotExist:
            return False

    @classmethod
    async def set_topic(cls, chat_id: int, topic_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=topic_id)

    @classmethod
    async def remove_topic(cls, chat_id: int):
        await cls.filter(chat_id=chat_id).update(topic_id=None)

    @classmethod
    async def get_by_integration(cls, integration_id: int) -> list:
        chats = await cls.all()
        for chat in chats:
            for integration in chat.integrations:
                if integration["integration_id"] == integration_id:
                    return chat


class Integration(models.Integration):
    @classmethod
    async def get_count(cls) -> int:
        return await cls.all().count()

    @classmethod
    async def get_by_code(cls, code: str) -> Union[models.Integration, bool]:
        try:
            return await cls.get(code=code)
        except DoesNotExist:
            return False

    @classmethod
    async def get_by_id(cls, integration_id: int) -> Union[models.Integration, bool]:
        try:
            return await cls.get(id=integration_id)
        except DoesNotExist:
            return False

    @classmethod
    async def create_integration(cls, repo: str) -> models.Integration:
        return await cls(
            repo=repo,
            code="".join(random.choices(string.ascii_uppercase + string.digits, k=16)),
        ).save()

    @classmethod
    async def update_last_commit(cls, integration_id: int, commit: str):
        await cls.filter(id=integration_id).update(last_commit=commit)

    @classmethod
    async def delete(cls, integration_id: int):
        await cls.filter(id=integration_id).delete()
