import sys
import os
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
    
    # Lógica para abrir arquivo via argumento de linha de comando (nth file.txt)
    if len(sys.argv) > 1 and sys.argv[1]:
        file_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(file_path):
            from core.src.buffer import BufferManager
            ctx = AppContext()
            
            content = BufferManager.read_file(file_path)
            ctx.editor_container.set_text(content)
            ctx.current_file = file_path
            ctx.is_dirty = False
            
            # Atualiza UI após carregar
            if ctx.status_bar:
                ctx.status_bar.update_status(1, 0, file_path)
            if ctx.py_plugin:
                ctx.py_plugin.highlight()

    app.mainloop()