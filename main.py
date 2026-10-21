import sys
import os
import importlib.util
import customtkinter as ctk

try:
    import notohiis_core
except ModuleNotFoundError as erro:
    raise SystemExit(
        "Core nativo (Rust) não compilado — rode: bash core/native/build.sh"
    ) from erro

notohiis_core.set_project_root(os.path.dirname(os.path.abspath(__file__)))

from ui.window import MainWindow
from notohiis_core import AppContext
from notohiis_core import AutocompleteEngine

PLUGIN_LOAD_DELAY_MS = 150

def load_plugins():
    ctx = AppContext()
    try:
        from core.core_plugin.git_plugin import GitPlugin
        ctx.git_plugin = GitPlugin()
    except Exception as e:
        ctx.git_plugin = None
        print(f"[CORE] Git Plugin indisponível: {e}")

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

    try:
        from core.core_plugin.tagpoints_plugin import TagPointsPlugin
        ctx.tp_plugin = TagPointsPlugin()
        ctx.tp_plugin.setup(ctx)
    except ImportError:
        print("[CORE] Tag Points Plugin não encontrado.")

    try:
        from core.core_plugin.global_search_engine import GlobalSearchEngine
        ctx.global_search_engine = GlobalSearchEngine()
    except ImportError:
        print("[CORE] Global Search Engine não encontrado.")

def load_external_plugins():
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

def open_startup_file():
    if len(sys.argv) < 2 or not sys.argv[1]:
        return

    file_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(file_path):
        return

    from notohiis_core import BufferManager
    ctx = AppContext()
    if hasattr(ctx, 'tab_bridge') and ctx.tab_bridge:
        ctx.tab_bridge.open_file(file_path)
    else:
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

def start_after_open():
    load_external_plugins()
    open_startup_file()

if __name__ == "__main__":
    # Configuração de tema do CustomTkinter
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    # Inicializa Engine de Autocomplete no Contexto Global
    AppContext().autocomplete_engine = AutocompleteEngine()

    # Inicializa a Janela (UI)
    app = MainWindow()

    load_plugins()

    app.after(PLUGIN_LOAD_DELAY_MS, start_after_open)

    app.mainloop()