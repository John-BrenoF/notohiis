#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import customtkinter as ctk
from core.src.app_context import AppContext

class ReplaceBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=70, corner_radius=0, **kwargs)
        self.ctx = AppContext()

        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=10, pady=(5, 2))
        
        self.entry = ctk.CTkEntry(self.frame_top, placeholder_text="Buscar...", width=300)
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", lambda e: self._navigate(1))
        self.entry.bind("<Escape>", lambda e: self.hide())
        
        self.lbl_count = ctk.CTkLabel(self.frame_top, text="0/0", width=50)
        self.lbl_count.pack(side="left", padx=5)

        self.btn_prev = ctk.CTkButton(self.frame_top, text="Anterior", width=60, command=lambda: self._navigate(-1))
        self.btn_prev.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(self.frame_top, text="Próximo", width=60, command=lambda: self._navigate(1))
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_close = ctk.CTkButton(self.frame_top, text="X", width=30, fg_color="#d16666", hover_color="#a85252", command=self.hide)
        self.btn_close.pack(side="right")

        self.frame_bottom = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_bottom.pack(fill="x", padx=10, pady=(2, 5))

        self.replace_entry = ctk.CTkEntry(self.frame_bottom, placeholder_text="Substituir por...", width=300)
        self.replace_entry.pack(side="left")
        
        self.replace_entry.bind("<Escape>", lambda e: self.hide())
        self.replace_entry.bind("<Return>", self._handle_enter)
        self.replace_entry.bind("<Control-Return>", self._replace_all_custom)
        
        for widget in (self.entry, self.replace_entry):
            widget.bind("<Up>", lambda e: self._navigate_custom(-1))
            widget.bind("<Down>", lambda e: self._navigate_custom(1))

        self.btn_replace = ctk.CTkButton(self.frame_bottom, text="Substituir", width=100, command=self._replace)
        self.btn_replace.pack(side="left", padx=(55, 5))

        self.btn_replace_all = ctk.CTkButton(self.frame_bottom, text="Substituir Tudo", width=120, command=self._replace_all)
        self.btn_replace_all.pack(side="left", padx=5)

        self.apply_theme()

    def apply_theme(self):
        tema = self.ctx.theme
        if not tema: return

        bg_color = tema.get("editor", {}).get("bg", "#1e1e1e")
        fg_color = tema.get("editor", {}).get("fg", "#d4d4d4")
        entry_bg = tema.get("editor", {}).get("selection_bg", "#2d2d30")
        btn_hover = tema.get("editor", {}).get("gutter_bg", "#3e3e42")

        self.configure(fg_color=bg_color)
        self.entry.configure(fg_color=entry_bg, text_color=fg_color, border_color=btn_hover)
        self.replace_entry.configure(fg_color=entry_bg, text_color=fg_color, border_color=btn_hover)
        self.lbl_count.configure(text_color=fg_color)
        
        self.btn_prev.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
        self.btn_next.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
        self.btn_replace.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
        self.btn_replace_all.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)

    def update_count(self, current, total):
        if total == 0:
            self.lbl_count.configure(text="0/0")
        else:
            self.lbl_count.configure(text=f"{current}/{total}")

    def _on_type(self, event):
        if event.keysym in ("Return", "Escape", "Up", "Down", "Left", "Right"): return
        term = self.entry.get()
        if self.ctx.editor:
            current, total = self.ctx.editor.highlight_search(term)
            self.update_count(current, total)

    def _navigate(self, step):
        if self.ctx.editor:
            current, total = self.ctx.editor.goto_next_match(step)
            self.update_count(current, total)

    def _navigate_custom(self, step):
        self._navigate(step)
        return "break"

    def _handle_enter(self, event=None):
        if self.ctx.editor:
            term = self.entry.get()
            replacement = self.replace_entry.get()
            if not term: return "break"
            
            self.ctx.editor.replace_current(term, replacement)
        return "break"

    def _replace_all_custom(self, event=None):
        self._replace_all()
        return "break"

    def _replace(self):
        self._handle_enter()

    def _replace_all(self):
        if self.ctx.editor:
            term = self.entry.get()
            replacement = self.replace_entry.get()
            if term:
                self.ctx.editor.replace_all(term, replacement)
                self.update_count(0, 0)

    def show(self):
        self.grid(row=3, column=1, sticky="ew") 
        self.entry.focus_set()

    def hide(self):
        self.grid_forget()
        self.entry.delete(0, 'end')
        self.replace_entry.delete(0, 'end')
        self.update_count(0, 0)
        if self.ctx.editor:
            self.ctx.editor.clear_search_highlight()
            self.ctx.editor.textbox.focus_set()