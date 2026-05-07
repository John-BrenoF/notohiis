from typing import Optional, Any

class AppContext:
    """
    Singleton para gerenciar o estado global da aplicação e 
    permitir a comunicação entre componentes sem acoplamento direto.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            cls._instance.window = None
            cls._instance.editor = None
            cls._instance.sidebar = None
            cls._instance.status_bar = None
            cls._instance.current_file: Optional[str] = None
            cls._instance.project_root: Optional[str] = None
            cls._instance.is_dirty: bool = False
            # Registrador de Plugins
            cls._instance.git_plugin = None
            cls._instance.md_plugin = None
            cls._instance.py_plugin = None
        return cls._instance

    def set_window(self, window: Any):
        self.window = window

    def set_editor(self, editor_container: Any):
        self.editor_container = editor_container

    def set_sidebar(self, sidebar: Any):
        self.sidebar = sidebar

    def set_status_bar(self, status_bar: Any):
        self.status_bar = status_bar