# Dependências: pip install tkinterweb markdown2

import os
from typing import Optional
import customtkinter as ctk
import markdown2
from tkinterweb import HtmlFrame
from core.src.app_context import AppContext

MARKDOWN_EXTENSIONS = (".md", ".markdown", ".mdown", ".mkd")
MARKDOWN_EXTRAS = [
    "fenced-code-blocks", "tables", "break-on-newline", "strike",
    "task_list", "footnotes", "header-ids", "code-friendly",
    "cuddled-lists", "smarty-pants",
]

def get_dynamic_style(theme):
    editor = theme.get("editor", {})
    syntax = theme.get("syntax", {})
    accent = syntax.get("keyword", "#c678dd")
    return f"""
<style>
    ::-webkit-scrollbar {{ width: 10px; }}
    ::selection {{ background-color: {accent}; color: #ffffff; }}
    body {{ background-color: {editor.get('bg', '#1e1e1e')}; color: {editor.get('fg', '#d4d4d4')}; 
           font-family: 'Segoe UI', sans-serif; padding: 20px 30px; line-height: 1.65; }}
    h1, h2, h3, h4 {{ color: {syntax.get('definition', '#569cd6')}; border-bottom: 1px solid #3e4451; padding-bottom: 4px; }}
    a {{ color: {accent}; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background-color: {theme.get('sidebar', {}).get('hover', '#2d2d2d')}; 
           color: {syntax.get('string', '#ce9178')}; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; }}
    pre {{ background-color: #21252b; padding: 15px; border-radius: 5px; border: 1px solid #3e4451; overflow-x: auto; }}
    pre code {{ background-color: transparent; padding: 0; }}
    blockquote {{ border-left: 4px solid {accent}; padding-left: 15px; margin-left: 0; color: #9da5b4; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #3e4451; padding: 8px; }}
    th {{ background-color: #2c313a; color: {syntax.get('definition', '#569cd6')}; }}
    img {{ max-width: 100%; border-radius: 4px; }}
    hr {{ border: none; border-top: 1px solid #3e4451; margin: 20px 0; }}
    input[type="checkbox"] {{ margin-right: 6px; }}
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
        self.btn_view = None
        self.last_rendered_content = {} # Cache para evitar re-renderização

    def _inject_status_button(self):
        """Injeta o botão de toggle na StatusBar do AppContext."""
        if self.ctx.status_bar:
            self.btn_view = ctk.CTkButton(
                self.ctx.status_bar,
                text="👁 View Mode",
                width=90,
                height=20,
                font=("Segoe UI", 10),
                command=self.toggle_preview
            )
            # Inicia oculto, será exibido via update_button_visibility

    def update_button_visibility(self, file_path: Optional[str]):
        """Mostra ou oculta o botão dependendo da extensão do arquivo."""
        # Tenta injetar o botão caso a StatusBar tenha sido criada após a carga do plugin
        if not self.btn_view:
            self._inject_status_button()
        
        if not self.btn_view: return # StatusBar ainda não disponível
        
        if file_path and file_path.lower().endswith(MARKDOWN_EXTENSIONS):
            self.btn_view.pack(side="right", padx=10)
        else:
            self.btn_view.pack_forget()

    def _render_html(self, file_path, text_content):
        if self.last_rendered_content.get(file_path) == text_content:
            return
        try:
            html_content = markdown2.markdown(text_content, extras=MARKDOWN_EXTRAS)
        except Exception as e:
            html_content = f"<h3>Erro ao renderizar Markdown</h3><pre>{e}</pre>"
        style = get_dynamic_style(self.ctx.theme)
        self.html_view.load_html(f"{style}{html_content}")
        self.last_rendered_content[file_path] = text_content

    def toggle_preview(self, event=None):
        """Alterna o estado de visualização."""
        if not self.ctx.current_file or not self.ctx.current_file.lower().endswith(MARKDOWN_EXTENSIONS):
            return "break"

        # O editor implementa a interface TextEditor, mas aqui precisamos
        # acessar as propriedades de widget (grid) para alternar a visualização.
        editor = self.ctx.editor 
        if not editor:
            return "break"

        file_path = self.ctx.current_file
        is_preview_active = self.view_states.get(file_path, False)

        if not self.html_view:
            self.html_view = HtmlFrame(editor)
        
        if not is_preview_active:
            # Converter Markdown para HTML
            text_content = editor.get_text()
            self._render_html(file_path, text_content)
            
            # Ocultar componentes do editor
            editor.textbox.grid_remove()
            editor.line_numbers.grid_remove()
            editor.git_margin.grid_remove()
            
            # Exibir HTML Frame ocupando toda a grade
            self.html_view.grid(row=0, column=0, columnspan=3, sticky="nsew")
            
            self.view_states[file_path] = True
            if self.btn_view:
                self.btn_view.configure(fg_color="#1f538d", text="✎ Preview ON")
        else:
            # Restaurar componentes do editor
            self.html_view.grid_remove()
            editor.textbox.grid(row=0, column=2, sticky="nsew")
            editor.line_numbers.grid(row=0, column=0, sticky="ns")
            editor.git_margin.grid(row=0, column=1, sticky="ns")
            
            self.view_states[file_path] = False
            if self.btn_view:
                self.btn_view.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="👁 View Mode")

        return "break"