from tortoise import fields
from tortoise.models import Model

from enum import Enum


class EventType(str, Enum):
    ping = "ping"
    push = "push"
    issues = "issues"
    star = "star"
    create = "create"
    pull_request = "pull_request"


class User(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField()
    token = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class EventSetting(Model):
    id = fields.BigIntField(pk=True)
    chat = fields.ForeignKeyField(
        "models.Chat", related_name="event_settings", on_delete=fields.CASCADE
    )
    event_type = fields.CharEnumField(EventType)
    enabled = fields.BooleanField(default=True)


class Chat(Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField()
    topic_id = fields.BigIntField(null=True)
    floodwait = fields.IntField(default=0)


class Integration(Model):
    id = fields.BigIntField(pk=True)
    repository_name = fields.CharField(max_length=255, null=True)
    integration_token = fields.CharField(max_length=255, null=True)

    chat = fields.ForeignKeyField(
        "models.Chat", related_name="integrations", on_delete=fields.CASCADE
    )
    user = fields.ForeignKeyField(
        "models.User", related_name="integrations", on_delete=fields.CASCADE
    )

    created_at = fields.DatetimeField(auto_now_add=True)
