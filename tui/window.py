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
        ("alt+up", "navigate_up", "Navegar Cima"),
        ("alt+down", "navigate_down", "Navegar Baixo"),
        ("q", "quit", "Sair"),
    ]

    def __init__(self):
        super().__init__()
        self.navigation_mode = None  # "up" ou "down" para navegação rápida
        self.navigation_timer_id = None

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

    def action_navigate_up(self) -> None:
        """Inicia modo de navegação para cima (aguardando número)."""
        self.navigation_mode = "up"
        self._schedule_navigation_timeout()

    def action_navigate_down(self) -> None:
        """Inicia modo de navegação para baixo (aguardando número)."""
        self.navigation_mode = "down"
        self._schedule_navigation_timeout()

    def _schedule_navigation_timeout(self) -> None:
        """Agenda timeout para cancelar navegação se não houver número."""
        if self.navigation_timer_id:
            self.remove_timer(self.navigation_timer_id)
        self.navigation_timer_id = self.set_timer(self._cancel_navigation, delay=1.0)

    def _cancel_navigation(self) -> None:
        """Cancela modo de navegação."""
        self.navigation_mode = None
        self.navigation_timer_id = None

    def _handle_quick_navigation(self, lines: int) -> None:
        """Executa navegação rápida se em modo ativo."""
        if self.navigation_mode:
            ctx = AppContext()
            if ctx.editor and hasattr(ctx.editor, 'move_cursor_by_lines'):
                ctx.editor.move_cursor_by_lines(lines, self.navigation_mode)
            self.navigation_mode = None
            if self.navigation_timer_id:
                self.remove_timer(self.navigation_timer_id)
                self.navigation_timer_id = None

    def on_key(self, event) -> None:
        """Captura eventos de teclado para navegação rápida."""
        # Verifica se estamos em modo de navegação e se é um número 1-9
        if self.navigation_mode and event.character and event.character.isdigit():
            lines = int(event.character)
            if 1 <= lines <= 9:
                self._handle_quick_navigation(lines)
                event.prevent_default()

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