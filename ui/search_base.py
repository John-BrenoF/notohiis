#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

"""
Base compartilhada para SearchBar e ReplaceBar.
Elimina a duplicação de lógica de busca e navegação.
"""

import customtkinter as ctk
from core.src.app_context import AppContext


class SearchBase(ctk.CTkFrame):
    """Classe base para barras de busca com lógica compartilhada."""

    def __init__(self, master, height: int = 35, **kwargs):
        super().__init__(master, height=height, corner_radius=0, **kwargs)
        self.ctx = AppContext()
        # Linha do grid da janela onde a barra é mostrada.
        # O TerminalPlugin a desloca para 4 porque ele ocupa as linhas 2 e 3.
        self.bar_row = 3

    def _create_entry(self, parent, placeholder_text: str = "Buscar...", width: int = 300) -> ctk.CTkEntry:
        """Cria um campo de entrada de busca com bindings padrão."""
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder_text, width=width)
        entry.bind("<KeyRelease>", self._on_type)
        entry.bind("<Return>", lambda e: self._navigate(1))
        entry.bind("<Escape>", lambda e: self.hide())
        return entry

    def _create_nav_button(self, parent, text: str, command, width: int = 60) -> ctk.CTkButton:
        """Cria um botão de navegação (Anterior/Próximo)."""
        return ctk.CTkButton(parent, text=text, width=width, command=command)

    def _create_close_button(self, parent, command) -> ctk.CTkButton:
        """Cria o botão de fechar (X) vermelho."""
        return ctk.CTkButton(
            parent, text="X", width=30,
            fg_color="#d16666", hover_color="#a85252",
            command=command
        )

    def update_count(self, current: int, total: int) -> None:
        """Atualiza o label de contagem de resultados."""
        if hasattr(self, 'lbl_count'):
            self.lbl_count.configure(text="0/0" if total == 0 else f"{current}/{total}")

    def _on_type(self, event) -> None:
        """Callback de digitação - busca em tempo real."""
        if event.keysym in ("Return", "Escape", "Up", "Down", "Left", "Right"):
            return
        term = self.entry.get()
        if self.ctx.editor:
            current, total = self.ctx.editor.highlight_search(term)
            self.update_count(current, total)

    def _navigate(self, step: int) -> None:
        """Navega entre os resultados da busca."""
        if self.ctx.editor:
            current, total = self.ctx.editor.goto_next_match(step)
            self.update_count(current, total)

    def show(self) -> None:
        """Mostra a barra de busca."""
        self.grid(row=self.bar_row, column=1, sticky="ew")
        self.entry.focus_set()

    def hide(self) -> None:
        """Oculta a barra de busca e limpa o highlight."""
        self.grid_forget()
        self.entry.delete(0, 'end')
        if hasattr(self, 'lbl_count'):
            self.update_count(0, 0)
        if self.ctx.editor:
            self.ctx.editor.clear_search_highlight()
            self.ctx.editor.textbox.focus_set()

    def _apply_theme_to_entry(self, entry: ctk.CTkEntry) -> None:
        """Aplica o tema a um campo de entrada."""
        tema = self.ctx.theme
        if not tema:
            return
        bg_color = tema.get("editor", {}).get("bg", "#1e1e1e")
        fg_color = tema.get("editor", {}).get("fg", "#d4d4d4")
        entry_bg = tema.get("editor", {}).get("selection_bg", "#2d2d30")
        btn_hover = tema.get("editor", {}).get("gutter_bg", "#3e3e42")
        entry.configure(fg_color=entry_bg, text_color=fg_color, border_color=btn_hover)
        return bg_color, fg_color, btn_hover

    def _apply_theme_to_button(self, button: ctk.CTkButton, bg_color: str, btn_hover: str, fg_color: str) -> None:
        """Aplica o tema a um botão."""
        button.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
