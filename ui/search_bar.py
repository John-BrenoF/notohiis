#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

#[add] adição  do arquivo search_bar.py
import customtkinter as ctk
from core.src.app_context import AppContext

class SearchBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=35, corner_radius=0, **kwargs)
        self.ctx = AppContext()
        
        self.entry = ctk.CTkEntry(self, placeholder_text="Buscar...", width=300)
        self.entry.pack(side="left", padx=10, pady=5)
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._navigate(1))
        self.entry.bind("<Escape>", lambda e: self.hide())
        
        ctk.CTkButton(self, text="Anterior", width=60, command=lambda: self._navigate(-1)).pack(side="left", padx=5)
        ctk.CTkButton(self, text="Próximo", width=60, command=lambda: self._navigate(1)).pack(side="left", padx=5)
        ctk.CTkButton(self, text="X", width=30, fg_color="#d16666", hover_color="#a85252", command=self.hide).pack(side="right", padx=10)

    def _on_type(self, event):
        if event.keysym in ("Return", "Escape", "Up", "Down", "Left", "Right"): return
        term = self.entry.get()
        if self.ctx.editor:
            self.ctx.editor.highlight_search(term)

    def _navigate(self, step):
        if self.ctx.editor:
            self.ctx.editor.goto_next_match(step)

    def show(self):
        self.grid(row=3, column=1, sticky="ew") 
        self.entry.focus_set()

    def hide(self):
        self.grid_forget()
        self.entry.delete(0, 'end')
        if self.ctx.editor:
            self.ctx.editor.clear_search_highlight()
            self.ctx.editor.textbox.focus_set()