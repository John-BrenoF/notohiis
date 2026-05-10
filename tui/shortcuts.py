from core.src.app_context import AppContext
from core.src.buffer import BufferManager

class ShortcutManager:
    """Gerencia ações do terminal."""
    
    @staticmethod
    def toggle_sidebar():
        ctx = AppContext()
        if ctx.sidebar:
            ctx.sidebar.display = not ctx.sidebar.display

    @staticmethod
    def save_file():
        ctx = AppContext()
        if ctx.current_file and ctx.editor:
            content = ctx.editor.get_text()
            BufferManager.save_file(ctx.current_file, content)
            ctx.is_dirty = False

    @staticmethod
    def new_buffer():
        ctx = AppContext()
        if ctx.editor:
            ctx.editor.set_text("")
            ctx.current_file = None
            ctx.is_dirty = False