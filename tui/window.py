from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header
from tui.sidebar import Sidebar
from tui.editor_area import EditorArea
from tui.status_bar import StatusBar
from tui.shortcuts import ShortcutManager
from core.src.app_context import AppContext
from core.src.session import SessionManager
import os
import sys

class TuiWindow(App):
    """Janela principal TUI."""
    CSS = """
    #sidebar { width: 30; dock: left; }
    #editor { width: 1fr; }
    """
    BINDINGS = [
        ("ctrl+a", "select_all", "Selecionar Tudo"),
        ("ctrl+b", "toggle_sidebar", "Sidebar"),
        ("ctrl+s", "save", "Salvar"),
        ("ctrl+n", "new", "Novo"),
        ("q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        ctx = AppContext()
        ctx.project_root = SessionManager.load_session() or os.getcwd()
        
        yield Header()
        with Horizontal():
            yield Sidebar(ctx.project_root)
            yield EditorArea()
        yield StatusBar()

    def action_toggle_sidebar(self) -> None:
        ShortcutManager.toggle_sidebar()

    def action_select_all(self) -> None:
        """Seleciona todo o texto no editor TUI."""
        ctx = AppContext()
        if ctx.editor and hasattr(ctx.editor, 'select_all'):
            ctx.editor.select_all()

    def action_save(self) -> None:
        ShortcutManager.save_file()

    def action_new(self) -> None:
        ShortcutManager.new_buffer()

    def on_mount(self) -> None:
        self.title = "Notohiis TUI"
        
        # Lógica para abrir arquivo via argumento (ntht file.txt)
        if len(sys.argv) > 1 and sys.argv[1]:
            file_path = os.path.abspath(sys.argv[1])
            ctx = AppContext()
            ctx.current_file = file_path
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                from core.src.buffer import BufferManager
                content = BufferManager.read_file(file_path)
                editor = self.query_one(EditorArea)
                editor.set_text(content)
                
            # Atualiza o status bar se disponível
            if ctx.status_bar:
                ctx.status_bar.update_status(1, 0, file_path)

if __name__ == "__main__":
    app = TuiWindow()
    app.run()