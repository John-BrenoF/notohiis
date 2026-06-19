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
        self.smart_hide_enabled = getattr(self.ctx, "smart_tab_hiding", True)
        self.hide_after_id = None
        self._init_ui()
        self._update_tab_visibility()
        self.open_new_tab()

    def _init_ui(self):
        self.frame = ctk.CTkFrame(
            self.master,
            fg_color=self.ctx.theme.get("sidebar", {}).get("bg", "#21252b"),
            corner_radius=0
        )
        self.frame.grid(row=0, column=1, sticky="ew")

        self.master.grid_rowconfigure(0, weight=0)
        self.master.grid_rowconfigure(1, weight=1)

        self.hover_anchor = ctk.CTkFrame(self.frame, fg_color="transparent", height=6)
        self.hover_anchor.pack(fill="x", side="top")
        self.hover_anchor.bind("<Enter>", lambda e: self._on_enter())

        self.tab_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.tab_row.pack(fill="x", side="top")
        self.tab_row.bind("<Enter>", lambda e: self._on_enter())
        self.tab_row.bind("<Leave>", self._on_leave)

        self.scroll_frame = ctk.CTkFrame(self.tab_row, fg_color="transparent")
        self.scroll_frame.pack(fill="x", side="left", padx=(6, 0), pady=2)

        tab_bg = self.ctx.theme.get("sidebar", {}).get("bg", "#21252b")
        self.new_tab_button = ctk.CTkButton(
            self.tab_row,
            text="+",
            width=22,
            height=22,
            fg_color=tab_bg,
            hover_color=tab_bg,
            text_color=self._lighten_color(self.ctx.theme.get("sidebar", {}).get("fg", "#d4d4d4"), 0.15),
            border_width=0,
            corner_radius=0,
            command=self.open_new_tab
        )
        self.new_tab_button.pack(side="right", padx=6, pady=2)
        self.new_tab_button.bind("<Enter>", lambda e: self._on_enter())

    def _lighten_color(self, hex_color: str, amount: float = 0.2) -> str:
        """Retorna uma versão mais clara de uma cor hexadecimal."""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) != 6:
            return hex_color
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            return f"#{hex_color}"

        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_enter(self, event=None):
        if not self.smart_hide_enabled:
            return
        if self.hide_after_id:
            self.frame.after_cancel(self.hide_after_id)
            self.hide_after_id = None
        self._show_tab_contents()

    def _on_leave(self, event=None):
        if not self.smart_hide_enabled:
            return
        if self.hide_after_id:
            self.frame.after_cancel(self.hide_after_id)
        self.hide_after_id = self.frame.after(250, self._hide_tab_contents)

    def _show_tab_contents(self):
        if not self.tab_row.winfo_ismapped():
            self.tab_row.pack(fill="x", side="top")
        if self.hover_anchor.winfo_ismapped():
            self.hover_anchor.pack_forget()

    def _hide_tab_contents(self):
        if self.tab_row.winfo_ismapped():
            self.tab_row.pack_forget()
        if not self.hover_anchor.winfo_ismapped():
            self.hover_anchor.pack(fill="x", side="top")

    def _update_tab_visibility(self):
        if self.smart_hide_enabled:
            self._hide_tab_contents()
        else:
            self._show_tab_contents()

    def set_smart_hide(self, enabled: bool):
        self.smart_hide_enabled = enabled
        self.ctx.smart_tab_hiding = enabled
        self._update_tab_visibility()

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
        current_tabs = self.ctx.tab_manager.get_tabs()
        current_ids = {tab.id for tab in current_tabs}

        for tab_id in list(self.tab_buttons.keys()):
            if tab_id not in current_ids:
                tab_frame, _, _ = self.tab_buttons[tab_id]
                tab_frame.destroy()
                del self.tab_buttons[tab_id]

        tab_bg = self.ctx.theme.get("sidebar", {}).get("bg", "#21252b")
        active_fg = self._lighten_color(self.ctx.theme.get("sidebar", {}).get("fg", "#d4d4d4"), 0.4)
        inactive_fg = self._lighten_color(self.ctx.theme.get("sidebar", {}).get("fg", "#d4d4d4"), 0.1)
        close_color = self._lighten_color(self.ctx.theme.get("sidebar", {}).get("fg", "#d4d4d4"), 0.15)

        for tab in current_tabs:
            active = self.ctx.tab_manager.active_tab_id == tab.id

            if tab.id in self.tab_buttons:
                tab_frame, button, close_button = self.tab_buttons[tab.id]
                
                tab_frame.pack(side="left", padx=(0, 4), pady=2)
                
                button.configure(text=tab.display_name, text_color=active_fg if active else inactive_fg)
            else:
                tab_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
                tab_frame.pack(side="left", padx=(0, 4), pady=2)

                button = ctk.CTkButton(
                    tab_frame,
                    text=tab.display_name,
                    width=110,
                    height=22,
                    corner_radius=0,
                    fg_color=tab_bg,
                    hover_color=tab_bg,
                    text_color=active_fg if active else inactive_fg,
                    border_width=0,
                    anchor="w",
                    command=lambda value=tab.id: self.select_tab(value)
                )
                button.pack(side="left")
                button.bind("<Enter>", lambda e: self._on_enter())

                close_button = ctk.CTkButton(
                    tab_frame,
                    text="✕",
                    width=18,
                    height=22,
                    corner_radius=0,
                    fg_color=tab_bg,
                    hover_color=tab_bg,
                    text_color=close_color,
                    border_width=0,
                    command=lambda value=tab.id: self.close_tab(value)
                )
                close_button.pack(side="left", padx=(1, 0))
                close_button.bind("<Enter>", lambda e: self._on_enter())

                self.tab_buttons[tab.id] = (tab_frame, button, close_button)