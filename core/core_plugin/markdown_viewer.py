# Dependências: pip install tkinterweb markdown2

import os
from typing import Optional
import customtkinter as ctk
import markdown2
from tkinterweb import HtmlFrame
from core.src.app_context import AppContext

def get_dynamic_style(theme):
    editor = theme.get("editor", {})
    syntax = theme.get("syntax", {})
    return f"""
<style>
    body {{ background-color: {editor.get('bg', '#1e1e1e')}; color: {editor.get('fg', '#d4d4d4')}; 
           font-family: 'Segoe UI', sans-serif; padding: 20px; line-height: 1.6; }}
    h1, h2, h3 {{ color: {syntax.get('definition', '#569cd6')}; border-bottom: 1px solid #3e4451; }}
    code {{ background-color: {theme.get('sidebar', {}).get('hover', '#2d2d2d')}; 
           color: {syntax.get('string', '#ce9178')}; padding: 2px 5px; border-radius: 3px; }}
    pre {{ background-color: #21252b; padding: 15px; border-radius: 5px; border: 1px solid #3e4451; }}
    blockquote {{ border-left: 4px solid {syntax.get('keyword', '#c678dd')}; padding-left: 15px; color: #9da5b4; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #3e4451; padding: 8px; }}
    th {{ background-color: #2c313a; color: {syntax.get('definition', '#569cd6')}; }}
</style>
"""
class MarkdownPlugin:
    """
    Plugin para visualização básica de Markdown.
    Alterna entre edição pura e modo de visualização formatado.
    """
    def __init__(self):
        self.ctx = AppContext()
        self.view_states = {} 
        self.html_view = None
        self.last_rendered_content = {} # Cache para evitar re-renderização

    def _inject_status_button(self):
        """Injeta o botão de toggle na StatusBar do AppContext."""
        if self.ctx.status_bar:
            self.btn_view = ctk.CTkButton(
                self.ctx.status_bar,
                text="View Mode",
                width=80,
                height=20,
                font=("Segoe UI", 10),
                command=self.toggle_preview
            )
            # Inicia oculto, será exibido via update_button_visibility

    def update_button_visibility(self, file_path: Optional[str]):
        """Mostra ou oculta o botão dependendo da extensão do arquivo."""
        # Tenta injetar o botão caso a StatusBar tenha sido criada após a carga do plugin
        if not hasattr(self, 'btn_view'):
            self._inject_status_button()
        
        if not hasattr(self, 'btn_view'): return # StatusBar ainda não disponível
        
        if file_path and file_path.lower().endswith(".md"):
            self.btn_view.pack(side="right", padx=10)
        else:
            self.btn_view.pack_forget()

    def toggle_preview(self, event=None):
        """Alterna o estado de visualização."""
        if not self.ctx.current_file or not self.ctx.current_file.endswith(".md"):
            return "break"

        container = self.ctx.editor_container
        file_path = self.ctx.current_file
        is_preview_active = self.view_states.get(file_path, False)

        if not self.html_view:
            self.html_view = HtmlFrame(container)
        
        if not is_preview_active:
            # Converter Markdown para HTML
            text_content = container.get_text()
            
            # Só atualiza o HTML se o conteúdo mudou desde a última vez
            if self.last_rendered_content.get(file_path) != text_content:
                html_content = markdown2.markdown(text_content, extras=["fenced-code-blocks", "tables", "break-on-newline"])
                style = get_dynamic_style(self.ctx.theme)
                self.html_view.load_html(f"{style}{html_content}")
                self.last_rendered_content[file_path] = text_content
            
            # Ocultar componentes do editor
            container.textbox.grid_remove()
            container.line_numbers.grid_remove()
            container.git_margin.grid_remove()
            
            # Exibir HTML Frame ocupando toda a grade
            self.html_view.grid(row=0, column=0, columnspan=3, sticky="nsew")
            
            self.view_states[file_path] = True
            if hasattr(self, 'btn_view'):
                self.btn_view.configure(fg_color="#1f538d", text="Preview ON")
        else:
            # Restaurar componentes do editor
            self.html_view.grid_remove()
            container.textbox.grid(row=0, column=2, sticky="nsew")
            container.line_numbers.grid(row=0, column=0, sticky="ns")
            container.git_margin.grid(row=0, column=1, sticky="ns")
            
            self.view_states[file_path] = False
            if hasattr(self, 'btn_view'):
                self.btn_view.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="View Mode")
        