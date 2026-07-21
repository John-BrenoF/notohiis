#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import customtkinter as ctk
from ui.editor_area import EditorArea
from ui.sidebar import Sidebar
from ui.status_bar import StatusBar
from ui.shortcuts import ShortcutManager
from ui.search_bar import SearchBar 
from core.src.app_context import AppContext
from core.src.session import SessionManager
try:
    from ui.tab_bridge import TabBridge
except ImportError:
    TabBridge = None
try:
    from core.src.theme_manager import ThemeManager
except (ImportError, AttributeError):
    ThemeManager = None
import os

class MainWindow(ctk.CTk):
    """Janela principal do editor Notohiis."""
    def __init__(self):
        super().__init__()

        self.title("Notohiis")
        self.geometry("1100x700")
        
        # Configuração de Grid: Tab Bar (0), Editor (1), Status Bar (2), Search Bar (3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # Inicialização do Contexto
        self.ctx = AppContext()
        self.ctx.set_window(self)
        self.load_theme(SessionManager.load_theme_pref())
        self.ctx.project_root = SessionManager.load_session()
        self.ctx.smart_tab_hiding = SessionManager.get_ui_setting("smart_tab_hiding", True)
        self.ctx.current_file = "Novo Arquivo" 

        # Sidebar 
        self.sidebar = Sidebar(self, width=200, corner_radius=0) 
        self.ctx.set_sidebar(self.sidebar)

        # Editor Area
        self.editor = EditorArea(self)
        self.editor.grid(row=1, column=1, sticky="nsew")
        self.ctx.set_editor(self.editor)

        # Status Bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=1, sticky="ew")
        self.ctx.set_status_bar(self.status_bar)

        # Search Bar (Instanciada, salva no contexto, oculta por padrão)
        self.search_bar = SearchBar(self)
        self.ctx.search_bar = self.search_bar

        # Tab Bridge (opcional)
        self.tab_bridge = TabBridge(self.ctx, self) if TabBridge else None

        # Atalhos
        ShortcutManager.setup_shortcuts(self)

        if self.ctx.project_root:
            self.sidebar.refresh_explorer()
            self.status_bar.update_status(1, 0, f"Projeto: {self.ctx.project_root}")

    def load_theme(self, theme_name: str = None):
        if ThemeManager:
            try:
                theme = ThemeManager.load_theme(theme_name)
                name = theme_name or ThemeManager.get_theme_name(theme_name)
            except Exception:
                theme, name = {}, "default"
        else:
            theme, name = {}, "default"

        self.ctx.set_theme(theme, name)
        self.configure(fg_color=self.ctx.theme.get("editor", {}).get("bg", "#141417"))
        self._apply_theme_to_children()

    def apply_theme(self, theme_name: str):
        self.load_theme(theme_name)
        SessionManager.save_theme_pref(theme_name)
        if self.status_bar:
            self.status_bar.update_status(1, 0, self.ctx.current_file or "Novo Arquivo")

    def _apply_theme_to_children(self):
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.apply_theme()
        if hasattr(self, "editor") and self.editor:
            self.editor.apply_theme()
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.apply_theme()

    def _apply_theme_to_children(self):
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.apply_theme()
        if hasattr(self, "editor") and self.editor:
            self.editor.apply_theme()
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.apply_theme()
        # [Melhoria] Garante que a barra de pesquisa atualize a cor se o usuário mudar de tema em tempo real
        if hasattr(self, "search_bar") and self.search_bar:
            self.search_bar.apply_theme()