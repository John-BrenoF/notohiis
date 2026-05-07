from textual.widgets import TextArea
from core.src.app_context import AppContext

class EditorArea(TextArea):
    """Widget TUI para edição de texto."""
    def __init__(self, **kwargs):
        super().__init__(
            language="python",
            theme="vscode_dark",
            soft_wrap=False,
            show_line_numbers=True,
            id="editor",
            **kwargs
        )
        self.ctx = AppContext()

    def on_mount(self):
        self.ctx.set_editor(self)

    def on_change(self, event):
        self.ctx.is_dirty = True
        # Sincroniza posição do cursor no status bar (opcional no Textual)
        if self.ctx.status_bar:
            line, col = self.cursor_location
            self.ctx.status_bar.update_status(line + 1, col, self.ctx.current_file or "Novo Arquivo")

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str):
        self.load_text(text)
        self.ctx.is_dirty = False

    def load_text(self, text: str):
        super().load_text(text)
        self.ctx.is_dirty = False