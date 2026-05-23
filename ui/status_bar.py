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
        hover_color = theme.get("hover", "#2c313a")
        
        # Lado Esquerdo: Git e Arquivo
        self.git_button = ctk.CTkButton(
            self, 
            text="", 
            font=("Segoe UI", 11, "bold"), 
            text_color="#61afef",
            fg_color="transparent", 
            hover_color=hover_color,
            command=self._on_git_click,
            width=0 # Largura automática
        )
        self.git_button.pack(side="left", padx=(5, 2))
        
        # Separador visual
        self.left_sep = ctk.CTkLabel(self, text="|", text_color="#3e4451", font=("Segoe UI", 12))
        self.left_sep.pack(side="left", padx=5)

        self.file_label = ctk.CTkLabel(self, text="Novo Arquivo", font=("Segoe UI", 11, "italic"), text_color=fg)
        self.file_label.pack(side="left", padx=(2, 10))

        # Lado Direito: Posição, Linguagem, Encoding
        self.encoding_label = ctk.CTkLabel(self, text="UTF-8", font=("Segoe UI", 11), text_color=fg)
        self.encoding_label.pack(side="right", padx=(10, 15))

        self.right_sep2 = ctk.CTkLabel(self, text="|", text_color="#3e4451", font=("Segoe UI", 12))
        self.right_sep2.pack(side="right", padx=2)

        self.lang_button = ctk.CTkButton(
            self, 
            text="Plain Text", 
            font=("Segoe UI", 11), 
            text_color=fg,
            fg_color="transparent",
            hover_color=hover_color,
            command=self._on_lang_click,
            width=0
        )
        self.lang_button.pack(side="right", padx=5)

        self.right_sep1 = ctk.CTkLabel(self, text="|", text_color="#3e4451", font=("Segoe UI", 12))
        self.right_sep1.pack(side="right", padx=2)

        self.pos_label = ctk.CTkLabel(self, text="Ln 1, Col 0", font=("Segoe UI", 11), text_color=fg)
        self.pos_label.pack(side="right", padx=(10, 5))

    def apply_theme(self):
        theme = AppContext().theme.get("status_bar", {})
        self.configure(fg_color=theme.get("bg", "#21252b"))
        fg = theme.get("fg", "#9da5b4")
        hover_color = theme.get("hover", "#2c313a")

        self.file_label.configure(text_color=fg)
        self.encoding_label.configure(text_color=fg)
        self.pos_label.configure(text_color=fg)
        self.lang_button.configure(text_color=fg, hover_color=hover_color)
        self.git_button.configure(hover_color=hover_color)
        self.left_sep.configure(text_color=theme.get("fg", "#3e4451"))
        self.right_sep1.configure(text_color=theme.get("fg", "#3e4451"))
        self.right_sep2.configure(text_color=theme.get("fg", "#3e4451"))

    def update_git_ui(self, status_text: str, is_dirty: bool):
        """Atualiza a aparência do botão Git com base no estado."""
        self.git_button.configure(text=status_text)
        if is_dirty:
            self.git_button.configure(text_color="#e06c75")
        else:
            self.git_button.configure(text_color="#61afef")

    def _on_git_click(self):
        ctx = AppContext()
        if ctx.git_plugin:
            ctx.git_plugin.quick_commit_ui()
            
    def _on_lang_click(self):
        messagebox.showinfo("Linguagem", "Funcionalidade de seleção de linguagem em desenvolvimento.", parent=self)

    def update_status(self, line: int, column: int, file_path: str = "Novo Arquivo"):
        ctx = AppContext()
        
        # Obter total de linhas para um feedback mais completo
        total_lines = str(ctx.editor.get_line_count()) if ctx.editor else "1"

        # Atualiza Posição do Cursor (Formato IDE: Linha, Coluna (Total))
        self.pos_label.configure(text=f"Ln {line}, Col {column} (Total: {total_lines})")
        
        # Atualiza Nome do Arquivo e Indicador de Modificação (●)
        if file_path and os.path.isabs(file_path):
            name = os.path.basename(file_path)
        else:
            name = file_path or "Novo Arquivo"
            
        dirty_indicator = " ●" if ctx.is_dirty else ""
        self.file_label.configure(text=f"{name}{dirty_indicator}", font=("Segoe UI", 11, "normal" if not ctx.is_dirty else "bold"))

        # Detecção Simples de Linguagem
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        langs = {'.py': 'Python', '.md': 'Markdown', '.json': 'JSON', '.txt': 'Plain Text'}
        self.lang_button.configure(text=langs.get(ext, 'Plain Text'))
        
        # Hook para plugin de Git
        if ctx.git_plugin:
            ctx.git_plugin.async_update_status()