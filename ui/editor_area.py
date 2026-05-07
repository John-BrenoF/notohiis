import customtkinter as ctk
from core.src.app_context import AppContext

class EditorArea(ctk.CTkTextbox):
    """Widget principal de edição de texto."""
    def __init__(self, master, **kwargs):
        super().__init__(
            master, 
            undo=True, 
            font=("Consolas", 15), 
            corner_radius=0, 
            border_width=0,
            **kwargs
        )
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<ButtonRelease-1>", self._on_key_release)

    def _on_key_release(self, event=None):
        """Atualiza a StatusBar com a posição do cursor."""
        ctx = AppContext()
        if ctx.status_bar:
            # index retorna "linha.coluna"
            cursor_pos = self.index(ctk.INSERT).split(".")
            line = cursor_pos[0]
            col = cursor_pos[1]
            ctx.status_bar.update_status(line, col, ctx.current_file or "Novo Arquivo")