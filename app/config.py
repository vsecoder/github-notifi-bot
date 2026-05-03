# sourcery skip: avoid-builtin-shadow
import os
from dataclasses import MISSING, dataclass, fields
from typing import Optional

import toml


@dataclass
class ConfigBot:
    token: str


@dataclass
class ConfigDatabase:
    models: list[str]
    protocol: str = "sqlite"
    file_name: str = "production-database.sqlite3"
    user: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None

    def get_db_url(self):
        if self.protocol == "sqlite":
            return f"{self.protocol}://{self.file_name}"
        return f"{self.protocol}://{self.user}:{self.password}@{self.host}:{self.port}"

    def get_tortoise_config(self):
        return {
            "connections": {"default": self.get_db_url()},
            "apps": {
                "models": {
                    "models": self.models,
                    "default_connection": "default",
                },
            },
        }


@dataclass
class ConfigSettings:
    owner_id: int
    throttling_rate: float = 0.5
    drop_pending_updates: bool = True


@dataclass
class ConfigApi:
    id: int = 2040
    hash: str = "b18441a1ff607e10a989891a5462e627"
    bot_api_url: str = "https://api.telegram.org"
    host: str = "localhost:4454"

    @property
    def is_local(self):
        return self.bot_api_url != "https://api.telegram.org"


@dataclass
class Config:
    bot: ConfigBot
    database: ConfigDatabase
    settings: ConfigSettings
    api: ConfigApi

    @classmethod
    def parse(cls, data: dict) -> "Config":
        sections: dict[str, object] = {}

        for section in fields(cls):
            section_type = section.type  # type: ignore[assignment]
            pre: dict[str, object] = {}
            current = data[section.name]

            for field in fields(section_type):  # type: ignore[arg-type]
                if field.name in current:
                    pre[field.name] = current[field.name]
                elif field.default is not MISSING:
                    pre[field.name] = field.default
                else:
                    raise ValueError(
                        f"Missing field {field.name} in section {section.name}"
                    )

            sections[section.name] = section_type(**pre)  # type: ignore[operator]

        return cls(**sections)  # type: ignore[arg-type]


def parse_config(config_file: str = "config.toml") -> Config:
    if not os.path.isfile(config_file) and not config_file.endswith(".toml"):
        config_file += ".toml"

    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file} no such file")

    with open(config_file, "r") as f:
        data = toml.load(f)

    return Config.parse(dict(data))
