import customtkinter as ctk
from core.src.app_context import AppContext

class StatusBar(ctk.CTkFrame):
    """Barra inferior para exibição de métricas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, height=22, corner_radius=0, **kwargs)
        theme = AppContext().theme.get("status_bar", {})
        self.configure(fg_color=theme.get("bg", "#007acc"))
        fg = theme.get("fg", "white")
        
        # Seção Esquerda: Git e Arquivo
        self.git_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11, "bold"), text_color=fg)
        self.git_label.pack(side="left", padx=(15, 10))
        
        self.file_label = ctk.CTkLabel(
            self, 
            text="Novo Arquivo", 
            font=("Segoe UI", 11),
            text_color=fg
        )
        self.file_label.pack(side="left", padx=5)

        # Seção Direita: Cursor e Encoding
        self.info_label = ctk.CTkLabel(
            self, 
            text="Linha: 1, Coluna: 0 | UTF-8", 
            font=("Segoe UI", 11),
            text_color=fg
        )
        self.info_label.pack(side="right", padx=20)

    def update_status(self, line: int, column: int, file_path: str = "Novo Arquivo"):
        self.info_label.configure(text=f"Ln {line}, Col {column} | UTF-8")
        self.file_label.configure(text=file_path)
        
        # Hook para plugin de Git
        from core.src.app_context import AppContext
        ctx = AppContext()
        if ctx.git_plugin:
            ctx.git_plugin.async_update_status()