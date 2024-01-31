from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField()
    token = fields.CharField(max_length=255, null=True)


class Chat(Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField()
    # [{user_id: ..., integration_id: ...}...]
    integrations = fields.JSONField(default=[])
    topic_id = fields.BigIntField(null=True)


class Integration(Model):
    id = fields.BigIntField(pk=True)
    repo = fields.CharField(max_length=255, null=True)
    code = fields.CharField(max_length=255, null=True)
