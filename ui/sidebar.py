#______________[português]____________________
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import customtkinter as ctk
import tkinter as tk
import os
from core.src.file_manager import FileManager
from core.src.app_context import AppContext
from core.src.buffer import BufferManager
from ui.sidebar_context import SidebarContextMenu

class Sidebar(ctk.CTkFrame):
    """Explorador de arquivos lateral."""
    
    DIR_ICON = "󰉋 "
    DEFAULT_ICON = "󰈔 "
    ICON_MAP = {
        '.py': ' ',
        '.md': '󰍔 ',
        '.json': ' ',
        '.txt': '󰈙 ',
        '.sh': '󱆃 ',
        '.gitignore': '󰊢 ',
        '.session_config': '󰒓 ',
        '.html': ' ',
        '.css': ' ',
        '.js': ' '
    }

    @classmethod
    def register_plugin_icons(cls, new_icons=None, dir_icon=None, default_icon=None):
        if dir_icon:
            cls.DIR_ICON = dir_icon
        if default_icon:
            cls.DEFAULT_ICON = default_icon
        if new_icons:
            cls.ICON_MAP.update({k.lower(): v for k, v in new_icons.items()})

    def __init__(self, master, width=0, corner_radius=0, **kwargs):
        super().__init__(
            master, 
            width=width, 
            corner_radius=corner_radius, 
            **kwargs
        )
        self.grid_propagate(False)
        self.item_widgets = {}
        self.item_paths_ordered = []
        self.selected_paths = []
        self.last_clicked_path = None
        theme = AppContext().theme.get("sidebar", {})
        self.configure(fg_color=theme.get("bg", "#1a1a1c"))
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(15, 10), padx=14)
        
        self.label = ctk.CTkLabel(self.header_frame, text="EXPLORER", font=("Segoe UI", 11, "bold"), text_color=theme.get("label", "gray"))
        self.label.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            self.header_frame, text="󰑐", width=24, height=24, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), font=("Segoe UI", 14), command=self.refresh_explorer
        )
        self.refresh_btn.pack(side="right")

        self.new_folder_btn = ctk.CTkButton(
            self.header_frame, text="󰉋", width=24, height=24, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), font=("Segoe UI", 14), command=lambda: self._show_inline_entry(is_dir=True)
        )
        self.new_folder_btn.pack(side="right", padx=2)

        self.new_file_btn = ctk.CTkButton(
            self.header_frame, text="󰈔", width=24, height=24, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), font=("Segoe UI", 14), command=lambda: self._show_inline_entry(is_dir=False)
        )
        self.new_file_btn.pack(side="right", padx=2)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, 
            corner_radius=0, 
            fg_color="transparent",
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370")
        )
        self.scrollable_frame.pack(fill="both", expand=True)
        
        self.scrollable_frame._scrollbar.configure(width=8)

        self.sidebar_context = SidebarContextMenu(self)
        self.bind("<Button-3>", self._show_context_menu)
        self.refresh_explorer()

    def apply_theme(self):
        theme = AppContext().theme.get("sidebar", {})
        self.configure(fg_color=theme.get("bg", "#1a1a1c"))
        self.label.configure(text_color=theme.get("label", "gray"))
        self.refresh_btn.configure(hover_color=theme.get("hover", "#2d2d2d"), text_color=theme.get("label", "gray"))
        self.new_folder_btn.configure(hover_color=theme.get("hover", "#2d2d2d"), text_color=theme.get("label", "gray"))
        self.new_file_btn.configure(hover_color=theme.get("hover", "#2d2d2d"), text_color=theme.get("label", "gray"))
        self.scrollable_frame.configure(
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370")
        )

        for p, btn in self.item_widgets.items():
            btn.configure(text_color=theme.get("fg", "#cccccc"), hover_color=theme.get("hover", "#2d2d2d"))
        self._update_selection_ui()

    def refresh_explorer(self):
        self.item_widgets.clear()
        self.item_paths_ordered.clear()
        self.selected_paths.clear()
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        ctx = AppContext()
        if not ctx.project_root:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum diretório\naberto", text_color="gray").pack(pady=40)
            return

        try:
            items = FileManager.list_directory(ctx.project_root)
        except Exception as e:
            self._show_error(f"Erro ao ler diretório:\n{str(e)}")
            return
        
        if ctx.project_root != "/" and os.path.dirname(ctx.project_root) != ctx.project_root:
            self._add_item("..", os.path.dirname(ctx.project_root), True)

        for item in items:
            self._add_item(item["name"], item["path"], item["is_dir"])

    def _get_icon(self, name, is_dir):
        if is_dir:
            return self.DIR_ICON
        ext = os.path.splitext(name)[1].lower()
        return self.ICON_MAP.get(ext, self.DEFAULT_ICON)

    def _add_item(self, name, path, is_dir):
        icon = self._get_icon(name, is_dir)
        theme = AppContext().theme.get("sidebar", {})
        self.item_paths_ordered.append(path)
        
        btn = ctk.CTkButton(
            self.scrollable_frame, 
            text=f"{icon}    {name}",
            anchor="w",
            fg_color="transparent",
            text_color=theme.get("fg", "#cccccc"),
            hover_color=theme.get("hover", "#2d2d2d"),
            font=("Segoe UI", 12),
            height=26,
            corner_radius=4
        )
        btn.pack(fill="x", padx=4, pady=1)
        self.item_widgets[path] = btn
        
        # Binds para seleção e clique
        btn.bind("<Button-1>", lambda e, p=path, d=is_dir: self._on_left_click(e, p, d, "none"))
        btn.bind("<Control-Button-1>", lambda e, p=path, d=is_dir: self._on_left_click(e, p, d, "ctrl"))
        btn.bind("<Shift-Button-1>", lambda e, p=path, d=is_dir: self._on_left_click(e, p, d, "shift"))
        btn.bind("<Button-3>", lambda e: self._show_context_menu(e, path))
        
        self._bind_scroll_to_widget(btn)

    def _on_left_click(self, event, path, is_dir, modifier="none"):
        if modifier == "ctrl":
            if path in self.selected_paths:
                self.selected_paths.remove(path)
            else:
                self.selected_paths.append(path)
            self.last_clicked_path = path
        elif modifier == "shift" and self.last_clicked_path in self.item_paths_ordered:
            idx1 = self.item_paths_ordered.index(self.last_clicked_path)
            idx2 = self.item_paths_ordered.index(path)
            start, end = min(idx1, idx2), max(idx1, idx2)
            self.selected_paths = self.item_paths_ordered[start:end+1]
        else:
            self.selected_paths = [path]
            self.last_clicked_path = path
            self._handle_click(path, is_dir)

        self._update_selection_ui()

    def _update_selection_ui(self):
        theme = AppContext().theme.get("sidebar", {})
        default_bg = "transparent"
        selected_bg = theme.get("selected", "#3a3f4b")
        for p, btn in self.item_widgets.items():
            if p in self.selected_paths:
                btn.configure(fg_color=selected_bg)
            else:
                btn.configure(fg_color=default_bg)

    def _bind_scroll_to_widget(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if hasattr(self.scrollable_frame, "_on_mousewheel"):
            self.scrollable_frame._on_mousewheel(event)
            return "break"
        canvas = getattr(self.scrollable_frame, "_parent_canvas", None)
        if canvas and hasattr(canvas, "yview_scroll"):
            direction = -1 if (event.num == 4 or event.delta > 0) else 1
            canvas.yview_scroll(direction, "units")
        return "break"

    def _handle_click(self, path, is_dir):
        ctx = AppContext()
        if is_dir:
            ctx.project_root = path
            self.refresh_explorer()
        else:
            try:
                if hasattr(ctx, 'tab_bridge') and ctx.tab_bridge:
                    ctx.tab_bridge.open_file(path)
                else:
                    ctx.current_file = path
                    ctx.is_dirty = False
                    content = BufferManager.read_file(path)
                    if ctx.editor:
                        ctx.editor.set_text(content)
                    if ctx.status_bar:
                        ctx.status_bar.update_status(1, 0, path)
                    if ctx.py_plugin:
                        ctx.py_plugin.highlight()
            except Exception as e:
                self._show_error(f"Erro ao abrir arquivo:\n{str(e)}")

    def _show_inline_entry(self, is_dir=False, target_path=None):
        ctx = AppContext()
        if not ctx.project_root: return

        anchor_widget = self.item_widgets.get(target_path) if target_path else None
        inline_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#2c313a", height=28, corner_radius=4)
        
        if anchor_widget:
            inline_frame.pack(fill="x", padx=4, pady=2, after=anchor_widget)
        else:
            children = self.scrollable_frame.winfo_children()
            inline_frame.pack(fill="x", padx=4, pady=2, before=children[0] if children else None)

        icon = self.DIR_ICON if is_dir else self.DEFAULT_ICON
        icon_label = ctk.CTkLabel(inline_frame, text=icon, font=("Segoe UI", 12))
        icon_label.pack(side="left", padx=(8, 4))
        
        entry = ctk.CTkEntry(
            inline_frame, height=22, font=("Segoe UI", 11), border_width=1,
            border_color="#3e4451", fg_color="#1d2026", text_color="#cccccc"
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=3)
        entry.focus_set()

        self._bind_scroll_to_widget(inline_frame)
        self._bind_scroll_to_widget(icon_label)
        self._bind_scroll_to_widget(entry)

        def confirm(event=None):
            name = entry.get().strip()
            if name:
                base_dir = ctx.project_root
                if target_path:
                    base_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
                new_path = os.path.join(base_dir, name)
                try:
                    if is_dir: 
                        FileManager.create_directory(new_path)
                    else: 
                        FileManager.create_file(new_path)
                    self.refresh_explorer()
                except Exception as e:
                    self._show_error(f"Erro ao criar:\n{str(e)}")
            inline_frame.destroy()

        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", lambda e: inline_frame.destroy())
        entry.bind("<FocusOut>", lambda e: inline_frame.destroy())

    def _show_context_menu(self, event, target_path=None):
        if target_path and target_path not in self.selected_paths:
            self.selected_paths = [target_path]
            self.last_clicked_path = target_path
            self._update_selection_ui()
        self.sidebar_context.show(event, self.selected_paths)

    def _center_dialog(self, dialog, width, height):
        dialog.update_idletasks()
        master = self.winfo_toplevel()
        dialog.transient(master)
        dialog.resizable(False, False)
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = max(0, (screen_width // 2) - (width // 2))
        y = max(0, (screen_height // 2) - (height // 2))
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _show_error(self, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Erro")
        dialog.attributes("-topmost", True)
        self._center_dialog(dialog, 320, 140)
        ctk.CTkLabel(dialog, text=message, pady=20, font=("Segoe UI", 11), justify="center").pack(padx=10, fill="both", expand=True)
        ctk.CTkButton(dialog, text="OK", width=80, command=dialog.destroy).pack(pady=(0, 15))