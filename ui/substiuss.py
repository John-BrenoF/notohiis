#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import customtkinter as ctk
from ui.search_base import SearchBase


class ReplaceBar(SearchBase):
    """Barra de busca e substituição (Ctrl+H)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=70, **kwargs)

        # ── Linha de busca ────────────────────────────────────────────
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=10, pady=(5, 2))

        self.entry = self._create_entry(self.frame_top, placeholder_text="Buscar...", width=300)
        self.entry.pack(side="left")

        self.lbl_count = ctk.CTkLabel(self.frame_top, text="0/0", width=50)
        self.lbl_count.pack(side="left", padx=5)

        self.btn_prev = self._create_nav_button(self.frame_top, "Anterior", lambda: self._navigate(-1))
        self.btn_prev.pack(side="left", padx=5)

        self.btn_next = self._create_nav_button(self.frame_top, "Próximo", lambda: self._navigate(1))
        self.btn_next.pack(side="left", padx=5)

        self.btn_close = self._create_close_button(self.frame_top, self.hide)
        self.btn_close.pack(side="right")

        # ── Linha de substituição ─────────────────────────────────────
        self.frame_bottom = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_bottom.pack(fill="x", padx=10, pady=(2, 5))

        self.replace_entry = ctk.CTkEntry(
            self.frame_bottom, placeholder_text="Substituir por...", width=300
        )
        self.replace_entry.pack(side="left")
        self.replace_entry.bind("<Escape>", lambda e: self.hide())
        self.replace_entry.bind("<Return>", self._handle_enter)
        self.replace_entry.bind("<Control-Return>", self._replace_all_custom)

        # Navegação e marcação compartilhada
        for widget in (self.entry, self.replace_entry):
            widget.bind("<Up>", lambda e: self._navigate(-1) or "break")
            widget.bind("<Down>", lambda e: self._navigate(1) or "break")
            widget.bind("<Alt-Left>", lambda e: self._toggle_mark(True) or "break")
            widget.bind("<Alt-Right>", lambda e: self._toggle_mark(False) or "break")

        self.btn_replace = ctk.CTkButton(
            self.frame_bottom, text="Substituir", width=100, command=self._replace_current
        )
        self.btn_replace.pack(side="left", padx=(55, 5))

        self.btn_replace_all = ctk.CTkButton(
            self.frame_bottom, text="Substituir Tudo", width=120, command=self._replace_all
        )
        self.btn_replace_all.pack(side="left", padx=5)

        self.apply_theme()

    def apply_theme(self):
        tema = self.ctx.theme
        if not tema:
            return

        bg_color, fg_color, btn_hover = self._apply_theme_to_entry(self.entry)
        if bg_color is None:
            return

        self.configure(fg_color=bg_color)
        self._apply_theme_to_entry(self.replace_entry)
        self.lbl_count.configure(text_color=fg_color)

        self._apply_theme_to_button(self.btn_prev, bg_color, btn_hover, fg_color)
        self._apply_theme_to_button(self.btn_next, bg_color, btn_hover, fg_color)
        self._apply_theme_to_button(self.btn_replace, bg_color, btn_hover, fg_color)
        self._apply_theme_to_button(self.btn_replace_all, bg_color, btn_hover, fg_color)

    # ── Ações de Substituição ────────────────────────────────────────────

    def _handle_enter(self, event=None):
        """Substitui o item marcado ou o item atual."""
        if self.ctx.editor:
            term = self.entry.get()
            replacement = self.replace_entry.get()
            if not term:
                return "break"

            if (hasattr(self.ctx.editor, 'marked_match_indices')
                    and self.ctx.editor.marked_match_indices):
                self.ctx.editor.replace_marked(term, replacement)
            else:
                self.ctx.editor.replace_current(term, replacement)
        return "break"

    def _replace_current(self):
        """Substitui o item atual e navega para o próximo."""
        self._handle_enter()

    def _replace_all(self):
        """Substitui todas as ocorrências."""
        if self.ctx.editor:
            term = self.entry.get()
            replacement = self.replace_entry.get()
            if term:
                self.ctx.editor.replace_all(term, replacement)
                self.update_count(0, 0)

    def _replace_all_custom(self, event=None):
        self._replace_all()
        return "break"

    def _toggle_mark(self, state: bool):
        """Alterna a marcação do resultado atual."""
        if self.ctx.editor:
            self.ctx.editor.toggle_mark_current(state)
        return "break"

    def hide(self):
        """Oculta a barra e limpa a busca."""
        super().hide()
        self.replace_entry.delete(0, 'end')
