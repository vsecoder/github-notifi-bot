from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField()
    token = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)


class Chat(Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField()
    topic_id = fields.BigIntField(null=True)


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
