#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

"""
AppContext - Singleton de estado global da aplicação.

Fornece comunicação entre componentes sem acoplamento direto.
Cada componente registra-se no contexto e pode acessar outros componentes
de forma desacoplada via este mediator.
"""

import os
from typing import Optional, Any, TYPE_CHECKING

from core.interfaces import TextEditor, StatusBar, Sidebar, AppWindow
from core.events import DIRTY_CHANGED, THEME_CHANGED, EventBus
from core.src.edit_history_manager import EditHistoryManager

if TYPE_CHECKING:
    from core.src.tab_manager import TabManager
    from core.src.autocomplete_engine import AutocompleteEngine


class AppContext:
    """
    Singleton para gerenciar o estado global da aplicação e
    permitir a comunicação entre componentes sem acoplamento direto.
    
    Componentes registrados:
        - window: Janela principal (AppWindow)
        - editor: Widget de edição (TextEditor)
        - sidebar: Explorador de arquivos (Sidebar)
        - status_bar: Barra de status (StatusBar)
        - tab_manager: Gerenciador de abas
        - tab_bridge: Ponte entre abas e UI
    
    Plugins:
        - git_plugin: Integração com Git
        - md_plugin: Visualização de Markdown
        - py_plugin: Sintaxe Python
        - autocomplete_engine: Engine de autocompletar
        - global_search_engine: Busca global
        - external_plugins: Lista de plugins externos
    """
    _instance: Optional["AppContext"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            ctx = cls._instance
            # --- Componentes UI ---
            ctx.window: Optional[AppWindow] = None
            ctx.editor: Optional[TextEditor] = None
            ctx.sidebar: Optional[Sidebar] = None
            ctx.status_bar: Optional[StatusBar] = None
            # --- Estado ---
            ctx.current_file: Optional[str] = None
            ctx.project_root: Optional[str] = None
            ctx.events = EventBus()
            ctx.edit_history = EditHistoryManager(ctx.events)
            ctx.events.on(DIRTY_CHANGED, ctx._on_dirty_changed)
            # --- Plugins Core ---
            ctx.git_plugin = None
            ctx.md_plugin = None
            ctx.py_plugin = None
            # --- Tema ---
            ctx.theme: dict = {}
            ctx.selected_theme: Optional[str] = None
            # --- Plugins Externos ---
            ctx.external_plugins: list = []
            # --- Engines ---
            ctx.autocomplete_engine: Optional[AutocompleteEngine] = None
            ctx.global_search_engine = None
            # --- Tab System ---
            ctx.smart_tab_hiding: bool = True
            ctx.tab_manager: Optional[TabManager] = None
            ctx.tab_bridge = None
            # --- Search/Replace Bars ---
            ctx.search_bar = None
            ctx.replace_bar = None
        return cls._instance

    @property
    def is_dirty(self) -> bool:
        """True se o conteúdo do editor foi modificado desde a última salvamento."""
        return self.edit_history.is_dirty

    @is_dirty.setter
    def is_dirty(self, dirty: bool) -> None:
        self.edit_history.set_dirty(dirty)

    # ── Registro de Componentes ──────────────────────────────────────────

    def set_window(self, window: AppWindow) -> None:
        self.window = window

    def set_editor(self, editor: TextEditor) -> None:
        self.editor = editor
        self.edit_history.attach_editor(editor)

    def set_sidebar(self, sidebar: Sidebar) -> None:
        self.sidebar = sidebar

    def set_status_bar(self, status_bar: StatusBar) -> None:
        self.status_bar = status_bar

    def set_theme(self, theme: dict, theme_name: Optional[str] = None) -> None:
        """Atualiza o tema global e notifica listeners de mudança de tema."""
        self.theme = theme or {}
        self.selected_theme = (
            os.path.splitext(os.path.basename(theme_name))[0]
            if theme_name else None
        )
        self.events.emit(THEME_CHANGED, self.theme)

    # ── Operações de Edição ──────────────────────────────────────────────

    def notify_save(self) -> None:
        """Marca o ponto atual na pilha de desfazer como o estado 'salvo'."""
        if self.editor:
            self.edit_history.mark_saved(self.editor.get_text())

    def handle_typing(self, char: Optional[str]) -> None:
        """Gerencia a entrada de texto para criar pontos de Undo granulares."""
        self.edit_history.on_text_input(char)

    def begin_transaction(self) -> None:
        """Inicia um grupo de operações que devem ser desfeitas juntas."""
        self.edit_history.begin_transaction()

    def end_transaction(self) -> None:
        """Finaliza o grupo de operações atômicas."""
        self.edit_history.end_transaction()

    def perform_undo(self) -> None:
        self.edit_history.perform_undo()

    def perform_redo(self) -> None:
        self.edit_history.perform_redo()

    # ── Callbacks Internos ───────────────────────────────────────────────

    def _on_dirty_changed(self, _dirty: bool) -> None:
        """Atualiza a StatusBar para refletir mudanças no estado Dirty."""
        if self.status_bar and self.editor:
            idx = self.editor.get_cursor_index()
            line, col = idx.split(".")
            self.status_bar.update_status(
                int(line), int(col),
                self.current_file or "Novo Arquivo"
            )
