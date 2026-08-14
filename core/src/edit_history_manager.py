#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

from typing import Optional
from core.events import EventBus
from core.interfaces import TextEditor

class EditHistoryManager:
    """Gerencia undo/redo e estado dirty do buffer ativo."""

    _LOGICAL_SEPARATORS = (
        " ", "\n", "\t", ".", ",", "!", "?", ";", ":", "(", "[", "{", "=", "+", "-", "*", "/", "\\"
    )

    def __init__(self, event_bus: EventBus):
        self._events = event_bus
        self._editor: Optional[TextEditor] = None
        self._baseline_content: str = ""
        self._transaction_level: int = 0
        self._chars_since_separator: int = 0
        self._is_replaying_history: bool = False
        self._dirty: bool = False

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def attach_editor(self, editor: TextEditor) -> None:
        self._editor = editor

    def on_content_loaded(self, content: str, baseline: Optional[str] = None, force_dirty: bool = False) -> None:
        if self._editor:
            self._editor.reset_undo_stack()
        self._baseline_content = content if baseline is None else baseline
        self._chars_since_separator = 0
        if force_dirty:
            self._set_dirty(True)
        else:
            self._set_dirty(content != self._baseline_content)

    def mark_saved(self, content: str) -> None:
        self._baseline_content = content
        self._set_dirty(False)

    def set_dirty(self, dirty: bool) -> None:
        self._set_dirty(dirty)

    def on_text_input(self, char: Optional[str]) -> None:
        if not self._editor or self._is_replaying_history:
            return

        self._sync_dirty_from_editor()

        if char is None or len(char) == 0:
            return

        self._chars_since_separator += 1
        if char in self._LOGICAL_SEPARATORS or self._chars_since_separator >= 15:
            self._editor.edit_separator()
            self._chars_since_separator = 0

    def begin_transaction(self) -> None:
        if self._transaction_level == 0 and self._editor:
            self._editor.begin_undo_group()
            self._chars_since_separator = 0
        self._transaction_level += 1

    def end_transaction(self) -> None:
        self._transaction_level = max(0, self._transaction_level - 1)
        if self._transaction_level == 0 and self._editor:
            self._editor.end_undo_group()
            self._sync_dirty_from_editor()

    def perform_undo(self) -> None:
        if not self._editor or self._is_replaying_history:
            return

        self._is_replaying_history = True
        try:
            self._editor.undo()
        finally:
            self._is_replaying_history = False

        self._chars_since_separator = 0
        self._sync_dirty_from_editor()

    def perform_redo(self) -> None:
        if not self._editor or self._is_replaying_history:
            return

        self._is_replaying_history = True
        try:
            self._editor.redo()
        finally:
            self._is_replaying_history = False

        self._chars_since_separator = 0
        self._sync_dirty_from_editor()

    def _sync_dirty_from_editor(self) -> None:
        if not self._editor:
            return
        self._set_dirty(self._editor.get_text() != self._baseline_content)

    def _set_dirty(self, dirty: bool) -> None:
        if dirty == self._dirty:
            return
        self._dirty = dirty
        self._events.emit("dirty_changed", dirty)
