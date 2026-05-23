import customtkinter as ctk
from ui.editor_area import EditorArea
from ui.sidebar import Sidebar
from ui.status_bar import StatusBar
from ui.shortcuts import ShortcutManager
from core.src.app_context import AppContext
from core.src.session import SessionManager
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
        
        # Configuração de Grid: Sidebar (0), Editor (1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar column, initially no weight
        self.grid_rowconfigure(0, weight=1)

        # Inicialização do Contexto
        self.ctx = AppContext()
        self.ctx.set_window(self)
        self.load_theme()
        self.ctx.project_root = SessionManager.load_session()
        self.ctx.current_file = "Novo Arquivo" # Default text for new buffer

        # Sidebar (Initially hidden, so not gridded)
        self.sidebar = Sidebar(self, width=200, corner_radius=0) # Give it a default width when visible
        # self.sidebar.grid(row=0, column=0, sticky="nsew", rowspan=2) # Do NOT grid it initially
        self.ctx.set_sidebar(self.sidebar)

        # Editor Area
        self.editor = EditorArea(self)
        self.editor.grid(row=0, column=1, sticky="nsew")
        # Registramos o container que contém o textbox e gutter
        self.ctx.set_editor(self.editor)

        # Status Bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.ctx.set_status_bar(self.status_bar)

        # Atalhos
        ShortcutManager.setup_shortcuts(self)

        # If a project root is loaded, refresh the sidebar
        if self.ctx.project_root:
            self.sidebar.refresh_explorer()
            self.status_bar.update_status(1, 0, f"Projeto: {self.ctx.project_root}")

    def load_theme(self, theme_name: str = None):
        """Carrega e aplica o tema selecionado."""
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
        """Aplica um novo tema em tempo de execução."""
        self.load_theme(theme_name)
        if self.status_bar:
            self.status_bar.update_status(1, 0, self.ctx.current_file or "Novo Arquivo")

    def _apply_theme_to_children(self):
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.apply_theme()
        if hasattr(self, "editor") and self.editor:
            self.editor.apply_theme()
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.apply_theme()