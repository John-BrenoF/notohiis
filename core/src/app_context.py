#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import os
from typing import Optional, Any
from core.interfaces import TextEditor, StatusBar, Sidebar, AppWindow
from core.events import EventBus
from core.src.edit_history_manager import EditHistoryManager

class AppContext:
    """
    Singleton para gerenciar o estado global da aplicação e 
    permitir a comunicação entre componentes sem acoplamento direto.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            cls._instance.window: Optional[AppWindow] = None
            cls._instance.editor: Optional[TextEditor] = None
            cls._instance.sidebar: Optional[Sidebar] = None
            cls._instance.status_bar: Optional[StatusBar] = None
            cls._instance.current_file: Optional[str] = None
            cls._instance.project_root: Optional[str] = None
            cls._instance.events = EventBus()
            cls._instance.edit_history = EditHistoryManager(cls._instance.events)
            cls._instance.events.on("dirty_changed", cls._instance._on_dirty_changed)
            # Registrador de Plugins
            cls._instance.git_plugin = None
            cls._instance.md_plugin = None
            cls._instance.py_plugin = None
            cls._instance.theme = {}
            cls._instance.selected_theme = None
            cls._instance.external_plugins = []
            cls._instance.autocomplete_engine = None
            cls._instance.smart_tab_hiding = True
            cls._instance.tab_manager = None
            cls._instance.tab_bridge = None
        return cls._instance

    @property
    def is_dirty(self) -> bool:
        return self.edit_history.is_dirty

    @is_dirty.setter
    def is_dirty(self, dirty: bool) -> None:
        self.edit_history.set_dirty(dirty)

    def set_window(self, window: AppWindow):
        self.window = window

    def set_editor(self, editor: TextEditor):
        self.editor = editor
        self.edit_history.attach_editor(editor)

    def set_sidebar(self, sidebar: Sidebar):
        self.sidebar = sidebar

    def set_status_bar(self, status_bar: StatusBar):
        self.status_bar = status_bar

    def set_theme(self, theme: dict, theme_name: Optional[str] = None):
        """Atualiza o tema global e notifica listeners de mudança de tema."""
        self.theme = theme or {}
        self.selected_theme = os.path.splitext(os.path.basename(theme_name))[0] if theme_name else None
        self.events.emit("theme_changed", self.theme)

    def notify_save(self):
        """
        Marca o ponto atual na pilha de desfazer como o estado 'salvo'.
        Chamado pelo BufferManager ou ShortcutManager após gravação em disco.
        """
        if self.editor:
            self.edit_history.mark_saved(self.editor.get_text())

    def handle_typing(self, char: Optional[str]):
        """
        Gerencia a entrada de texto para criar pontos de Undo granulares.
        Chamado pela UI a cada tecla pressionada.
        """
        self.edit_history.on_text_input(char)

    def begin_transaction(self):
        """Inicia um grupo de operações que devem ser desfeitas juntas."""
        self.edit_history.begin_transaction()

    def end_transaction(self):
        """Finaliza o grupo de operações atômicas."""
        self.edit_history.end_transaction()

    def perform_undo(self):
        self.edit_history.perform_undo()

    def perform_redo(self):
        self.edit_history.perform_redo()

    def _on_dirty_changed(self, _dirty: bool):
        """Atualiza a StatusBar para refletir mudanças no estado Dirty."""
        if self.status_bar and self.editor:
            idx = self.editor.get_cursor_index()
            line, col = idx.split(".")
            self.status_bar.update_status(int(line), int(col), self.current_file or "Novo Arquivo")
