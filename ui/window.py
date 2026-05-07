import customtkinter as ctk
from ui.editor_area import EditorArea
from ui.sidebar import Sidebar
from ui.status_bar import StatusBar
from ui.shortcuts import ShortcutManager
from core.src.app_context import AppContext
from core.src.session import SessionManager

class MainWindow(ctk.CTk):
    """Janela principal do editor Notohiis."""
    def __init__(self):
        super().__init__()

        self.title("Notohiis")
        self.geometry("1100x700")
        
        # Configuração de Grid: Sidebar (0), Editor (1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Inicialização do Contexto
        self.ctx = AppContext()
        self.ctx.set_window(self)
        self.ctx.project_root = SessionManager.load_session()

        # Sidebar
        self.sidebar = Sidebar(self, width=0, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", rowspan=2)
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
        