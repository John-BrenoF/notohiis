from typing import Optional, Any
from core.interfaces import TextEditor, StatusBar, Sidebar, AppWindow
from core.events import EventBus

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
            cls._instance.is_dirty: bool = False
            cls._instance.events = EventBus()
            # Registrador de Plugins
            cls._instance.git_plugin = None
            cls._instance.md_plugin = None
            cls._instance.py_plugin = None
            cls._instance.theme = {}
            cls._instance.external_plugins = []
            cls._instance.autocomplete_engine = None
        return cls._instance

    def set_window(self, window: AppWindow):
        self.window = window

    def set_editor(self, editor: TextEditor):
        self.editor = editor

    def set_sidebar(self, sidebar: Sidebar):
        self.sidebar = sidebar

    def set_status_bar(self, status_bar: StatusBar):
        self.status_bar = status_bar