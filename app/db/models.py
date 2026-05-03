from tortoise import fields
from tortoise.models import Model

from enum import Enum


class EventType(str, Enum):
    ping = "ping"
    push = "push"
    issues = "issues"
    issue_comment = "issue_comment"
    pull_request = "pull_request"
    pull_request_review = "pull_request_review"
    pull_request_review_comment = "pull_request_review_comment"
    commit_comment = "commit_comment"
    star = "star"
    fork = "fork"
    create = "create"
    delete = "delete"
    release = "release"
    workflow_run = "workflow_run"
    discussion = "discussion"
    discussion_comment = "discussion_comment"
    deployment_status = "deployment_status"
    member = "member"
    public = "public"


class AuthSource(str, Enum):
    """How an Integration was created — used to dispatch /reinstall, /delete
    and webhook routing to the right code path. ``pat`` for legacy/PAT-based
    integrations (webhook on ``/webhook/{integration_token}``); ``app`` for
    GitHub App-based integrations (webhook on the App-level ``/webhook``)."""
    pat = "pat"
    app = "app"


class User(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField()
    token = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Eventsetting(Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField()
    event_type = fields.CharField(max_length=50)
    enabled = fields.BooleanField(default=True)


class Chat(Model):
    id = fields.BigIntField(pk=True)
    chat_id = fields.BigIntField()
    topic_id = fields.BigIntField(null=True)
    floodwait = fields.IntField(default=0)


class Installation(Model):
    """A GitHub App installation owned by a Telegram user.

    One row per (telegram user, GitHub account) pair. ``installation_id`` is
    GitHub's id — needed to mint installation tokens and to route incoming
    webhook events back to the right Telegram-side data.
    """
    id = fields.BigIntField(pk=True)
    installation_id = fields.BigIntField(unique=True)
    account_login = fields.CharField(max_length=255)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="installations",
        on_delete=fields.CASCADE,
    )
    created_at = fields.DatetimeField(auto_now_add=True)


class Integration(Model):
    id = fields.BigIntField(pk=True)
    repository_name = fields.CharField(max_length=255, null=True)
    integration_token = fields.CharField(max_length=255, null=True)
    # How this integration was set up. Existing rows backfill to "pat".
    auth_source = fields.CharField(max_length=8, default=AuthSource.pat.value)
    # Set only for App-based integrations; null for PAT-based ones.
    installation = fields.ForeignKeyField(
        "models.Installation",
        related_name="integrations",
        null=True,
        on_delete=fields.SET_NULL,
    )

    chat = fields.ForeignKeyField(
        "models.Chat", related_name="integrations", on_delete=fields.CASCADE
    )
    user = fields.ForeignKeyField(
        "models.User", related_name="integrations", on_delete=fields.CASCADE
    )

    created_at = fields.DatetimeField(auto_now_add=True)
