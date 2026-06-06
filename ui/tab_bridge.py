import os
import tkinter as tk
import customtkinter as ctk
from core.src.app_context import AppContext
from core.src.buffer import BufferManager

try:
    from core.src.tab_manager import TabManager
except ImportError:
    TabManager = None

class TabBridge:
    """Ponte entre a UI e o TabManager opcional do core."""

    def __init__(self, ctx: AppContext, master):
        self.ctx = ctx
        self.master = master
        self.enabled = TabManager is not None
        self.tab_buttons = {}
        self.frame = None
        self.scroll_frame = None

        if not self.enabled:
            return

        self.ctx.tab_manager = TabManager()
        self.ctx.tab_bridge = self
        self._init_ui()
        self.open_new_tab()

    def _init_ui(self):
        self.frame = ctk.CTkFrame(self.master, fg_color=self.ctx.theme.get("sidebar", {}).get("bg", "#21252b"), corner_radius=0)
        self.frame.grid(row=0, column=1, sticky="ew")

        self.master.grid_rowconfigure(0, weight=0)
        self.master.grid_rowconfigure(1, weight=1)

        self.scroll_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.scroll_frame.pack(fill="x", side="left", padx=(8, 0), pady=4)

        self.new_tab_button = ctk.CTkButton(
            self.frame,
            text="+",
            width=32,
            height=30,
            fg_color=self.ctx.theme.get("sidebar", {}).get("button_bg", "#3b3f46"),
            hover_color=self.ctx.theme.get("sidebar", {}).get("hover", "#4b5260"),
            text_color=self.ctx.theme.get("sidebar", {}).get("fg", "#d4d4d4"),
            command=self.open_new_tab
        )
        self.new_tab_button.pack(side="right", padx=8, pady=4)

    def open_new_tab(self, path: str = None):
        if path:
            tab = self.ctx.tab_manager.open_file(path)
        else:
            tab = self.ctx.tab_manager.create_tab()
        self._render_tabs()
        self._load_tab(tab)
        return tab

    def open_file(self, path: str):
        tab = self.ctx.tab_manager.open_file(path)
        self._render_tabs()
        self._load_tab(tab)
        return tab

    def select_tab(self, tab_id: int):
        tab = self.ctx.tab_manager.select_tab(tab_id)
        if not tab:
            return None
        self._load_tab(tab)
        self._render_tabs()
        return tab

    def close_tab(self, tab_id: int):
        if not self.ctx.tab_manager.close_tab(tab_id, force=True):
            return False
        remaining = self.ctx.tab_manager.get_tabs()
        self._render_tabs()
        if remaining:
            self._load_tab(self.ctx.tab_manager.get_active_tab())
        else:
            self.open_new_tab()
        return True

    def save_active_tab(self) -> bool:
        active = self.ctx.tab_manager.get_active_tab()
        if not active:
            return False
        if active.path:
            if self.ctx.editor:
                active.content = self.ctx.editor.get_text()
            if self.ctx.tab_manager.save_active_tab():
                self.ctx.is_dirty = False
                if self.ctx.status_bar:
                    self.ctx.status_bar.update_status(1, 0, active.path)
                return True
        return False

    def update_active_tab_content(self, content: str):
        if not self.ctx.tab_manager:
            return
        self.ctx.tab_manager.update_active_content(content)
        active = self.ctx.tab_manager.get_active_tab()
        if active:
            self.ctx.is_dirty = active.is_dirty

    def _load_tab(self, tab):
        if not self.ctx.editor or not tab:
            return
        content = tab.content
        self.ctx.current_file = tab.path or tab.title
        self.ctx.is_dirty = tab.is_dirty
        self.ctx.editor.set_text(content)
        if self.ctx.status_bar:
            self.ctx.status_bar.update_status(1, 0, self.ctx.current_file)

    def _render_tabs(self):
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        self.tab_buttons.clear()

        for tab in self.ctx.tab_manager.get_tabs():
            active = self.ctx.tab_manager.active_tab_id == tab.id
            tab_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            tab_frame.pack(side="left", padx=(0, 4), pady=2)

            button = ctk.CTkButton(
                tab_frame,
                text=tab.display_name,
                width=140,
                height=30,
                corner_radius=8,
                fg_color="#2b2f33" if active else "#1f2124",
                hover_color="#3c4148",
                text_color="#ffffff",
                command=lambda value=tab.id: self.select_tab(value)
            )
            button.pack(side="left")

            close_button = ctk.CTkButton(
                tab_frame,
                text="✕",
                width=30,
                height=30,
                fg_color="#2b2f33" if active else "#1f2124",
                hover_color="#e06c75",
                text_color="#ffffff",
                command=lambda value=tab.id: self.close_tab(value)
            )
            close_button.pack(side="left", padx=(2, 0))
            self.tab_buttons[tab.id] = (button, close_button)
