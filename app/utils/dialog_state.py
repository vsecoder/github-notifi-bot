"""Pydantic-typed wrapper for ``aiogram_dialog`` ``dialog_data``.

Instead of scattering string-keyed dict access across handlers, each
dialog defines a ``DialogState`` subclass with explicit fields.

Usage:

    class ReposState(DialogState):
        selected_org: str | None = None
        selected_repo: str | None = None

    # In a handler:
    state = ReposState.load(manager)
    state.selected_org = "vsecoder"
    state.save(manager)

Pyright will catch typos in field names; runtime ignores unknown keys
(``extra="ignore"``) so dialog-internal aiogram_dialog state coexists
peacefully in the same dict.
"""
from typing import Type, TypeVar

from aiogram_dialog import DialogManager
from pydantic import BaseModel, ConfigDict


T = TypeVar("T", bound="DialogState")


class DialogState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @classmethod
    def load(cls: Type[T], manager: DialogManager) -> T:
        """Read state from the manager's ``dialog_data``. Missing fields
        fall back to the model's declared defaults."""
        return cls.model_validate(manager.dialog_data)

    def save(self, manager: DialogManager) -> None:
        """Persist state into the manager's ``dialog_data``."""
        manager.dialog_data.update(self.model_dump())
