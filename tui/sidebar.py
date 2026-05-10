from textual.widgets import DirectoryTree
import os
from core.src.app_context import AppContext

class Sidebar(DirectoryTree):
    """Explorador de arquivos TUI."""
    def __init__(self, path: str, **kwargs):
        super().__init__(path, id="sidebar", **kwargs)
        self.ctx = AppContext()

    def on_mount(self):
        self.ctx.set_sidebar(self)

    def refresh_explorer(self):
        # O DirectoryTree do Textual atualiza automaticamente o path
        if self.ctx.project_root:
            self.path = self.ctx.project_root

    def on_directory_tree_file_selected(self, event):
        from core.src.buffer import BufferManager
        path = str(event.path)
        content = BufferManager.read_file(path)
        if self.ctx.editor:
            self.ctx.editor.set_text(content)
        self.ctx.current_file = path
        self.ctx.is_dirty = False
        if self.ctx.status_bar:
            self.ctx.status_bar.update_status(1, 0, path)