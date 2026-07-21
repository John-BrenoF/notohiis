#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

#[add] adição  do arquivo search_bar.py
# ui/search_bar.py
import customtkinter as ctk
import json
import os
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
        
        self.btn_prev = ctk.CTkButton(self, text="Anterior", width=60, command=lambda: self._navigate(-1))
        self.btn_prev.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(self, text="Próximo", width=60, command=lambda: self._navigate(1))
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_close = ctk.CTkButton(self, text="X", width=30, fg_color="#d16666", hover_color="#a85252", command=self.hide)
        self.btn_close.pack(side="right", padx=10)

        # [Melhoria] Carrega e aplica o tema assim que a barra é instanciada
        self.apply_theme()

    def apply_theme(self):
        # [Melhoria] Leitura dinâmica do tema nas preferências e injeção de estilo na barra de busca
        try:
            with open("ui/preferencias/preferecia.json", "r", encoding="utf-8") as f:
                prefs = json.load(f)
                tema_nome = prefs.get("selected_theme", "default")
            
            with open(f"ui/estilo/{tema_nome}.json", "r", encoding="utf-8") as f:
                tema = json.load(f)

            # Adapte as chaves abaixo dependendo de como as cores estão estruturadas no seu JSON
            bg_color = tema.get("editor", {}).get("bg", "#1e1e1e")
            fg_color = tema.get("editor", {}).get("fg", "#d4d4d4")
            entry_bg = tema.get("editor", {}).get("selection_bg", "#2d2d30")
            btn_hover = tema.get("editor", {}).get("gutter_bg", "#3e3e42")

            self.configure(fg_color=bg_color)
            self.entry.configure(fg_color=entry_bg, text_color=fg_color, border_color=btn_hover)
            self.btn_prev.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
            self.btn_next.configure(fg_color=bg_color, hover_color=btn_hover, text_color=fg_color)
            
        except (FileNotFoundError, json.JSONDecodeError):
            pass # Se der merda na leitura do arquivo, mantém as cores padrão do customtkinter

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