import sys
import os
import importlib.util
import customtkinter as ctk
from ui.window import MainWindow
from core.src.app_context import AppContext
from core.src.autocomplete_engine import AutocompleteEngine

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

def load_external_plugins():
    """Carrega plugins dinamicamente da pasta plugins/."""
    ctx = AppContext()
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    
    if not os.path.exists(plugins_dir):
        return

    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"plugins.{filename[:-3]}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(plugins_dir, filename))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "setup"):
                    module.setup(ctx)
            except Exception as e:
                print(f"[PLUGIN] Falha ao carregar {filename}: {e}")

if __name__ == "__main__":
    # Configuração de tema do CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # Inicializa Engine de Autocomplete no Contexto Global
    AppContext().autocomplete_engine = AutocompleteEngine()

    # Inicializa a Janela (UI)
    app = MainWindow()

    load_plugins()
    load_external_plugins()

    # Lógica para abrir arquivo via argumento de linha de comando (nth file.txt)
    if len(sys.argv) > 1 and sys.argv[1]:
        file_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(file_path):
            from core.src.buffer import BufferManager
            ctx = AppContext()
            
            ctx.current_file = file_path
            ctx.is_dirty = False
            content = BufferManager.read_file(file_path)
            if ctx.editor:
                ctx.editor.set_text(content)
            
            # Atualiza UI após carregar
            if ctx.status_bar:
                ctx.status_bar.update_status(1, 0, file_path)
            if ctx.py_plugin:
                ctx.py_plugin.highlight()

    app.mainloop()