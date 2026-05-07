# Dependências Sugeridas: markdown, bleach (opcional para sanitização)
# Este plugin usa tags nativas do Tkinter para manter a independência de bibliotecas externas.

import re
import tkinter as tk
from core.src.app_context import AppContext

class MarkdownPlugin:
    """
    Plugin para visualização básica de Markdown.
    Alterna entre edição pura e modo de visualização formatado.
    """
    def __init__(self):
        self.ctx = AppContext()
        self.is_preview_mode = False
        self._setup_tags()

    def _setup_tags(self):
        """Configura os estilos de renderização na área de texto."""
        editor_textbox = self.ctx.editor_container.textbox
        editor_textbox.tag_config("H1", foreground="#569CD6") # Removed font
        editor_textbox.tag_config("BOLD") # Removed font, default bold might be applied by Tkinter if tag is present
        editor_textbox.tag_config("CODE", background="#2D2D2D", foreground="#CE9178") # Removed font

    def toggle_preview(self, event=None):
        """Alterna o estado de visualização."""
        if not self.ctx.current_file or not self.ctx.current_file.endswith(".md"):
            return "break"

        editor_widget = self.ctx.editor_container.textbox
        
        if not self.is_preview_mode:
            self._apply_markdown_tags(editor_widget)
            editor_widget.configure(state="disabled")
            self.is_preview_mode = True
        else:
            self._clear_tags(editor_widget)
            editor_widget.configure(state="normal")
            self.is_preview_mode = False
        
        return "break"

    def _apply_markdown_tags(self, widget: tk.Text):
        """Parser simples baseado em Regex para aplicar tags de estilo."""
        content = widget.get("1.0", tk.END)
        
        # H1: # Título
        for match in re.finditer(r"^#\s+(.*)$", content, re.MULTILINE):
            start, end = f"{match.start()+1}.0", f"{match.end()+1}.0"
            widget.tag_add("H1", start, end)

        # Bold: **texto**
        for match in re.finditer(r"\*\*(.*?)\*\*", content):
            # Conversão de offset para index de linha.coluna do Tkinter
            start_idx = self._offset_to_index(content, match.start())
            end_idx = self._offset_to_index(content, match.end())
            widget.tag_add("BOLD", start_idx, end_idx)

        # Code: `code`
        for match in re.finditer(r"`(.*?)`", content):
            start_idx = self._offset_to_index(content, match.start())
            end_idx = self._offset_to_index(content, match.end())
            widget.tag_add("CODE", start_idx, end_idx)

    def _clear_tags(self, widget: tk.Text):
        """Remove toda a formatação para modo de edição."""
        for tag in ["H1", "BOLD", "CODE"]:
            widget.tag_remove(tag, "1.0", tk.END)

    def _offset_to_index(self, content: str, offset: int) -> str:
        """Converte offset de string para o formato 'linha.coluna' do Tkinter."""
        lines = content[:offset].split('\n')
        line = len(lines)
        column = len(lines[-1])
        return f"{line}.{column}"