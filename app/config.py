# sourcery skip: avoid-builtin-shadow
import os
from typing import Optional

import toml
from pydantic import BaseModel, ConfigDict, Field


class _Section(BaseModel):
    """Common Pydantic config for every TOML section: ignore unknown keys
    so adding new fields in the future doesn't break older configs."""
    model_config = ConfigDict(extra="ignore")


class ConfigBot(_Section):
    token: str
    # Bot's @username, used for deep-link callbacks (GitHub App Setup URL,
    # `?startgroup=true`, etc.). Optional but recommended.
    username: Optional[str] = None


class ConfigDatabase(_Section):
    models: list[str]
    protocol: str = "sqlite"
    file_name: str = "production-database.sqlite3"
    user: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None

    def get_db_url(self) -> str:
        if self.protocol == "sqlite":
            return f"{self.protocol}://{self.file_name}"
        return (
            f"{self.protocol}://{self.user}:{self.password}"
            f"@{self.host}:{self.port}"
        )

    def get_tortoise_config(self) -> dict:
        return {
            "connections": {"default": self.get_db_url()},
            "apps": {
                "models": {
                    "models": self.models,
                    "default_connection": "default",
                },
            },
        }


class ConfigSettings(_Section):
    owner_id: int
    throttling_rate: float = 0.5
    drop_pending_updates: bool = True


class ConfigApi(_Section):
    id: int = 2040
    hash: str = "b18441a1ff607e10a989891a5462e627"
    bot_api_url: str = "https://api.telegram.org"
    host: str = "localhost:4454"

    @property
    def is_local(self) -> bool:
        return self.bot_api_url != "https://api.telegram.org"


class ConfigGitHubApp(_Section):
    """Optional GitHub App credentials. Considered "configured" only when
    ``app_id``, ``slug`` and ``private_key_path`` are all set."""
    app_id: int = 0
    slug: str = ""
    private_key_path: str = ""
    webhook_secret: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.slug and self.private_key_path)


class Config(_Section):
    bot: ConfigBot
    database: ConfigDatabase
    settings: ConfigSettings
    # Optional sections — missing in TOML means "use defaults".
    api: ConfigApi = Field(default_factory=ConfigApi)
    github_app: ConfigGitHubApp = Field(default_factory=ConfigGitHubApp)


def parse_config(config_file: str = "config.toml") -> Config:
    if not os.path.isfile(config_file) and not config_file.endswith(".toml"):
        config_file += ".toml"
    if not os.path.isfile(config_file):
        raise FileNotFoundError(
            f"Config file not found: {config_file} no such file"
        )
    with open(config_file, "r") as f:
        data = toml.load(f)
    return Config.model_validate(dict(data))
