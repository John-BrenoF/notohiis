#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.


import customtkinter as ctk
import os
from core.src.app_context import AppContext
from core.src.session import SessionManager
from ui.shortcuts import ShortcutManager

class QuickAccess(ctk.CTkToplevel):
    """Widget de acesso rápido para sessões recentes (Projetos)."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Acesso Rápido - Projetos Recentes")
        self.geometry("600x420")
        self.attributes("-topmost", True)
        self.grab_set()
        
        self.ctx = AppContext()
        theme = self.ctx.theme.get("sidebar", {})
        self.bg_color = theme.get("bg", "#1e1e20")
        self.hover_color = theme.get("hover", "#2c313a")
        self.configure(fg_color=self.bg_color)
        
        ShortcutManager._center_window(self, 600, 420)
        
        self.all_projects = SessionManager.get_recent_projects()
        self.visible_items = [] # Lista de tuplas (caminho, frame_widget, botao_widget)
        self.selected_index = 0

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="󰑓 Projetos Recentes", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        # Campo de Busca Ativo
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Digite para filtrar...", height=35, border_color="#333335")
        self.search_entry.pack(fill="x", padx=20, pady=5)
        self.search_entry.focus_set()
        
        # Scrollable area for sessions
        self.scroll = ctk.CTkScrollableFrame(
            self, 
            fg_color=self.bg_color, 
            corner_radius=10,
            scrollbar_button_color="#333335"
        )
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._render_list()
        
        # Footer
        ctk.CTkLabel(self, text="↑↓ Navegar | Enter Abrir | Esc Sair", font=("Segoe UI", 10), text_color="gray").pack(pady=5)
        
        # Bindings de Navegação
        self.bind("<Escape>", lambda e: self.destroy())
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.bind("<Up>", lambda e: self._move_selection(-1))
        self.bind("<Down>", lambda e: self._move_selection(1))
        self.bind("<Return>", lambda e: self._open_selected())

    def _render_list(self, filter_text=""):
        # Limpa widgets atuais
        for item in self.scroll.winfo_children():
            item.destroy()
        
        self.visible_items = []
        filtered = [p for p in self.all_projects if filter_text.lower() in p.lower()]
        
        if not filtered:
            ctk.CTkLabel(self.scroll, text="Nenhum projeto encontrado.", font=("Segoe UI", 12), text_color="gray").pack(pady=40)
            return

        for i, path in enumerate(filtered):
            exists = os.path.exists(path)
            name = os.path.basename(path) or path
            
            item_frame = ctk.CTkFrame(self.scroll, fg_color="transparent", height=50)
            item_frame.pack(fill="x", pady=2, padx=5)
            
            display_text = f"󰉋  {name}\n{path}"
            if not exists:
                display_text = f" fence  {name} (Não encontrado)\n{path}"

            btn = ctk.CTkButton(
                item_frame,
                text=display_text,
                anchor="w",
                font=("Segoe UI", 12),
                fg_color="transparent",
                hover_color=self.hover_color,
                text_color=None if exists else "#666666",
                height=45,
                command=lambda p=path: self._open_project(p)
            )
            btn.pack(fill="x")
            self.visible_items.append((path, item_frame, btn))
        
        self.selected_index = 0
        self._update_selection_visuals()

    def _on_search_key(self, event):
        if event.keysym in ("Up", "Down", "Return"):
            return
        self._render_list(self.search_entry.get())

    def _move_selection(self, direction):
        if not self.visible_items: return
        self.selected_index = (self.selected_index + direction) % len(self.visible_items)
        self._update_selection_visuals()

    def _update_selection_visuals(self):
        for i, (path, frame, btn) in enumerate(self.visible_items):
            if i == self.selected_index:
                frame.configure(fg_color=self.hover_color)
                btn.configure(fg_color=self.hover_color)
            else:
                frame.configure(fg_color="transparent")
                btn.configure(fg_color="transparent")

    def _open_selected(self):
        if self.visible_items:
            path = self.visible_items[self.selected_index][0]
            self._open_project(path)

    def _open_project(self, path):
        if os.path.exists(path):
            self.ctx.project_root = path
            SessionManager.save_session(path) # Atualiza ordem de recência
            if self.ctx.sidebar:
                self.ctx.sidebar.refresh_explorer()
            if self.ctx.status_bar:
                self.ctx.status_bar.update_status(1, 0, f"Projeto: {path}")
            self.destroy()
        else:
            # Caso a pasta tenha sido movida ou deletada
            pass