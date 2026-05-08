import customtkinter as ctk
import os
from core.src.app_context import AppContext
from tkinter import messagebox

class StatusBar(ctk.CTkFrame):
    """Barra inferior para exibição de métricas e estado da aplicação."""
    def __init__(self, master, **kwargs):
        super().__init__(master, height=25, corner_radius=0, **kwargs)
        theme = AppContext().theme.get("status_bar", {})
        self.configure(fg_color=theme.get("bg", "#21252b"))
        fg = theme.get("fg", "#9da5b4")
        
        # Lado Esquerdo: Git e Arquivo
        self.git_button = ctk.CTkButton(
            self, 
            text="", 
            font=("Segoe UI", 11, "bold"), 
            text_color="#61afef", # Cor azul para Git
            fg_color="transparent", 
            hover_color=theme.get("hover", "#2c313a"), # Cor de hover da sidebar
            command=self._on_git_click,
            width=0 # Largura automática
        )
        self.git_button.pack(side="left", padx=(10, 5))
        
        self.file_label = ctk.CTkLabel(self, text="Novo Arquivo", font=("Segoe UI", 11), text_color=fg)
        self.file_label.pack(side="left", padx=5)

        # Lado Direito: Posição, Linguagem, Encoding
        self.pos_label = ctk.CTkLabel(self, text="Ln 1, Col 0", font=("Segoe UI", 11), text_color=fg)
        self.pos_label.pack(side="right", padx=15)

        self.lang_button = ctk.CTkButton(
            self, 
            text="Plain Text", 
            font=("Segoe UI", 11), 
            text_color=fg,
            fg_color="transparent",
            hover_color=theme.get("hover", "#2c313a"),
            command=self._on_lang_click,
            width=0
        )
        self.lang_button.pack(side="right", padx=10)

        self.encoding_label = ctk.CTkLabel(self, text="UTF-8", font=("Segoe UI", 11), text_color=fg)
        self.encoding_label.pack(side="right", padx=10)

    def _on_git_click(self):
        ctx = AppContext()
        if ctx.git_plugin:
            ctx.git_plugin.quick_commit_ui()
            
    def _on_lang_click(self):
        messagebox.showinfo("Linguagem", "Funcionalidade de seleção de linguagem em desenvolvimento.", parent=self)

    def update_status(self, line: int, column: int, file_path: str = "Novo Arquivo"):
        ctx = AppContext()
        
        # Atualiza Posição do Cursor
        self.pos_label.configure(text=f"Ln {line}, Col {column}")
        
        # Atualiza Nome do Arquivo e Indicador de Modificação (●)
        name = os.path.basename(file_path) if file_path else "Novo Arquivo"
        status_prefix = "● " if ctx.is_dirty else ""
        self.file_label.configure(text=f"{status_prefix}{name}")

        # Detecção Simples de Linguagem
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        langs = {'.py': 'Python', '.md': 'Markdown', '.json': 'JSON', '.txt': 'Plain Text'}
        self.lang_button.configure(text=langs.get(ext, 'Plain Text'))
        
        # Hook para plugin de Git
        if ctx.git_plugin:
            ctx.git_plugin.async_update_status()