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


class SearchBar(SearchBase):
    """Barra de busca simples (Ctrl+F)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=35, **kwargs)

        self.entry = self._create_entry(self, placeholder_text="Buscar...", width=300)
        self.entry.pack(side="left", padx=10, pady=5)

        self.lbl_count = ctk.CTkLabel(self, text="0/0", width=50)
        self.lbl_count.pack(side="left", padx=5)

        self.btn_prev = self._create_nav_button(self, "Anterior", lambda: self._navigate(-1))
        self.btn_prev.pack(side="left", padx=5)

        self.btn_next = self._create_nav_button(self, "Próximo", lambda: self._navigate(1))
        self.btn_next.pack(side="left", padx=5)

        self.btn_close = self._create_close_button(self, self.hide)
        self.btn_close.pack(side="right", padx=10)

        self.apply_theme()

    def apply_theme(self):
        tema = self.ctx.theme
        if not tema:
            return

        bg_color, fg_color, btn_hover = self._apply_theme_to_entry(self.entry)
        if bg_color is None:
            return

        self.configure(fg_color=bg_color)
        self.lbl_count.configure(text_color=fg_color)
        self._apply_theme_to_button(self.btn_prev, bg_color, btn_hover, fg_color)
        self._apply_theme_to_button(self.btn_next, bg_color, btn_hover, fg_color)
