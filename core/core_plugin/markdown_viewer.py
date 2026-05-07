# Dependências: pip install tkinterweb markdown2

import os
import customtkinter as ctk
import markdown2
from tkinterweb import HtmlFrame
from core.src.app_context import AppContext

class MarkdownPlugin:
    """
    Plugin para visualização básica de Markdown.
    Alterna entre edição pura e modo de visualização formatado.
    """
    def __init__(self):
        self.ctx = AppContext()
        self.view_states = {} 
        self.html_view = None
        self._inject_status_button()

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
            self.btn_view.pack(side="right", padx=10)

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
            html_content = markdown2.markdown(text_content, extras=["fenced-code-blocks", "tables"])
            
            # Carregar no visualizador HTML
            self.html_view.load_html(html_content)
            
            # Ocultar componentes do editor
            container.textbox.grid_remove()
            container.line_numbers.grid_remove()
            container.git_margin.grid_remove()
            
            # Exibir HTML Frame ocupando toda a grade
            self.html_view.grid(row=0, column=0, columnspan=3, sticky="nsew")
            
            self.view_states[file_path] = True
            self.btn_view.configure(fg_color="#1f538d", text="Preview ON")
        else:
            # Restaurar componentes do editor
            self.html_view.grid_remove()
            container.textbox.grid()
            container.line_numbers.grid()
            container.git_margin.grid()
            
            self.view_states[file_path] = False
            self.btn_view.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="View Mode")
        