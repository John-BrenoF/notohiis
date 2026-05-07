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

class TuiWindow(App):
    """Janela principal TUI."""
    CSS = """
    #sidebar { width: 30; dock: left; }
    #editor { width: 1fr; }
    """
    BINDINGS = [
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

    def action_save(self) -> None:
        ShortcutManager.save_file()

    def action_new(self) -> None:
        ShortcutManager.new_buffer()

    def on_mount(self) -> None:
        self.title = "Notohiis TUI"

if __name__ == "__main__":
    app = TuiWindow()
    app.run()