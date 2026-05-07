import customtkinter as ctk
from ui.window import MainWindow
from core.src.app_context import AppContext

def load_plugins():
    """Carregamento dinâmico e seguro de plugins core."""
    ctx = AppContext()
    try:
        from core.core_plugin.git_plugin import GitPlugin
        ctx.git_plugin = GitPlugin()
    except ImportError:
        print("[CORE] Git Plugin não encontrado.")

    try:
        from core.core_plugin.markdown_viewer import MarkdownPlugin
        ctx.md_plugin = MarkdownPlugin()
    except ImportError:
        print("[CORE] Markdown Plugin não encontrado.")

    try:
        from core.core_plugin.python_syntax import PythonSyntaxPlugin
        ctx.py_plugin = PythonSyntaxPlugin()
    except ImportError:
        print("[CORE] Python Syntax Plugin não encontrado.")

if __name__ == "__main__":
    # Configuração de tema do CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    load_plugins()
    app = MainWindow()
    
    app.mainloop()