# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import os
import tkinter as tk
import customtkinter as ctk
from core.src.file_manager import FileManager
from core.src.app_context import AppContext


class InlineRename:
    def __init__(self, sidebar_instance, target_path, on_confirm_callback):
        self.sidebar_instance = sidebar_instance
        self.target_path = target_path
        self.on_confirm_callback = on_confirm_callback
        
        self.target_button = self.sidebar_instance.item_widgets.get(target_path)
        if not self.target_button:
            return

        button_text = self.target_button.cget("text")
        icon_text = button_text.split("    ")[0] if "    " in button_text else ""
        
        self.inline_frame = ctk.CTkFrame(
            self.sidebar_instance.scrollable_frame, 
            fg_color="#2c313a", 
            height=26, 
            corner_radius=4
        )
        self.inline_frame.pack(fill="x", padx=4, pady=1, before=self.target_button)
        self.target_button.pack_forget()
        
        if icon_text:
            self.icon_label = ctk.CTkLabel(self.inline_frame, text=icon_text, font=("Segoe UI", 12))
            self.icon_label.pack(side="left", padx=(8, 4))
            
        self.entry_field = ctk.CTkEntry(
            self.inline_frame, height=22, font=("Segoe UI", 11), border_width=1,
            border_color="#3e4451", fg_color="#1d2026", text_color="#cccccc"
        )
        self.entry_field.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=2)
        
        base_name = os.path.basename(self.target_path)
        self.entry_field.insert(0, base_name)
        self.entry_field.focus_set()
        
        name_without_extension, extension = os.path.splitext(base_name)
        if os.path.isfile(self.target_path) and extension:
            self.entry_field.select_range(0, len(name_without_extension))
        else:
            self.entry_field.select_range(0, tk.END)

        self.entry_field.bind("<Return>", self._confirm_rename_action)
        self.entry_field.bind("<Escape>", self._cancel_rename_action)
        self.entry_field.bind("<FocusOut>", self._cancel_rename_action)
        
        self.sidebar_instance._bind_scroll_to_widget(self.inline_frame)
        if icon_text:
            self.sidebar_instance._bind_scroll_to_widget(self.icon_label)
        self.sidebar_instance._bind_scroll_to_widget(self.entry_field)

    def _confirm_rename_action(self, event=None):
        new_name = self.entry_field.get().strip()
        if not new_name or new_name == os.path.basename(self.target_path):
            self._cancel_rename_action()
            return
            
        if FileManager.rename_path(self.target_path, new_name):
            new_path = os.path.join(os.path.dirname(self.target_path), new_name)
            self.on_confirm_callback(self.target_path, new_path)
        else:
            if hasattr(self.sidebar_instance, "_show_error"):
                self.sidebar_instance._show_error("Não foi possível renomear o item.")
                
        self._destroy_inline_components()

    def _cancel_rename_action(self, event=None):
        self._destroy_inline_components()
        self.sidebar_instance.refresh_explorer()

    def _destroy_inline_components(self):
        if self.inline_frame.winfo_exists():
            self.inline_frame.destroy()


class SidebarContextMenu:
    def __init__(self, sidebar):
        self.sidebar = sidebar
        self.popup = None
        self.theme = AppContext().theme.get("sidebar", {})
        self._menu_targets = []
        self._unbind_id = None

    def show(self, event, target_paths=None):
        self._menu_targets = target_paths or []
        self._close_menu()
        menu_bg = self.theme.get("menu_bg", "#282c34")
        border = self.theme.get("menu_border", "#3e4451")
        width = 240
        self.popup = ctk.CTkToplevel(self.sidebar)
        self.popup.overrideredirect(True)
        self.popup.lift()
        self.popup.wm_attributes("-topmost", True)
        self.popup.configure(fg_color=menu_bg)
        
        self.menu_frame = ctk.CTkFrame(self.popup, fg_color=menu_bg, border_width=1, border_color=border, corner_radius=6)
        self.menu_frame.pack(fill="both", expand=True)

        x = event.x_root
        y = event.y_root
        self.popup.geometry(f"{width}x1+{x}+{y}")
        self.popup.bind("<Escape>", lambda e: self._close_menu())
        self._build_menu()
        self.popup.update_idletasks()
        height = self.popup.winfo_reqheight()
        self.popup.geometry(f"{width}x{height}+{x}+{y}")
        self.popup.transient(self.sidebar.winfo_toplevel())
        self.popup.grab_set()
        self.popup.focus_force()
        self.popup.bind("<FocusOut>", lambda e: self._close_menu())
        self.popup.bind("<Button-1>", self._check_click_outside, add="+")

    def _check_click_outside(self, event):
        x, y = event.x_root, event.y_root
        x0 = self.popup.winfo_rootx()
        y0 = self.popup.winfo_rooty()
        x1 = x0 + self.popup.winfo_width()
        y1 = y0 + self.popup.winfo_height()
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            self._close_menu()

    def _build_menu(self):
        label_style = {
            "text_color": self.theme.get("menu_heading", "#7b828e"),
            "font": ("Segoe UI", 10, "bold"),
            "anchor": "w"
        }
        base_style = {
            "fg_color": "transparent",
            "hover_color": self.theme.get("menu_item_hover", "#3f4b61"),
            "text_color": self.theme.get("menu_fg", "#dcdfe4"),
            "corner_radius": 4,
            "height": 28,
            "border_width": 0,
            "anchor": "w",
            "font": ("Segoe UI", 11)
        }
        
        has_targets = len(self._menu_targets) > 0
        multi = len(self._menu_targets) > 1
        
        ctk.CTkFrame(self.menu_frame, height=4, fg_color="transparent").pack(fill="x")
        
        self._add_item("Novo Arquivo", self._menu_new_file, icon="\uf15b", **base_style)
        self._add_item("Nova Pasta", self._menu_new_folder, icon="\uf07b", **base_style)
        self._add_item("Renomear", self._menu_rename, icon="\uf044", **base_style, state="normal" if has_targets and not multi else "disabled")
        
        self._add_separator()

        self._add_item("Copiar Caminho Relativo", self._copy_relative_path, icon="\uf0c5", **base_style, state="normal" if has_targets else "disabled")
        self._add_item("Copiar Caminho Absoluto", self._copy_absolute_path, icon="\uf0c5", **base_style, state="normal" if has_targets else "disabled")
        
        self._add_separator()
        
        delete_style = base_style.copy()
        delete_style["text_color"] = "#e06c75"
        delete_style["hover_color"] = "#4a2530"
        self._add_item("Excluir", self._menu_delete, icon="\uf1f8", **delete_style, state="normal" if has_targets else "disabled")
        
        self._add_separator()
        
        ctk.CTkLabel(self.menu_frame, text="GIT", **label_style).pack(fill="x", padx=14, pady=(2, 2))
        
        self._add_item("Add (Stage)", self._git_add, icon="\uf067", **base_style, state="normal" if has_targets else "disabled")
        self._add_item("Reset (Unstage)", self._git_reset, icon="\uf0e2", **base_style, state="normal" if has_targets else "disabled")
        self._add_item("Ver Diff", self._git_diff, icon="\uf126", **base_style, state="normal" if has_targets else "disabled")
        
        ctk.CTkFrame(self.menu_frame, height=4, fg_color="transparent").pack(fill="x")
        
    def _add_item(self, label, command, icon="", **kwargs):
        btn = ctk.CTkButton(self.menu_frame, text=f"{icon}    {label}", command=lambda: self._action(command), **kwargs)
        btn.pack(fill="x", padx=6, pady=1)
        btn.bind("<Button-1>", lambda e: self._action(command) if kwargs.get("state") != "disabled" else None)

    def _add_separator(self):
        sep = ctk.CTkFrame(self.menu_frame, height=1, fg_color=self.theme.get("menu_separator", "#3e4451"))
        sep.pack(fill="x", padx=6, pady=4)

    def _action(self, command):
        self._close_menu()
        command()

    def _close_menu(self):
        if self.popup:
            try:
                self.popup.grab_release()
            except Exception:
                pass
            self.popup.destroy()
            self.popup = None

    def _menu_new_file(self):
        target = self._menu_targets[0] if self._menu_targets else None
        self.sidebar._show_inline_entry(is_dir=False, target_path=target)

    def _menu_new_folder(self):
        target = self._menu_targets[0] if self._menu_targets else None
        self.sidebar._show_inline_entry(is_dir=True, target_path=target)

    def _menu_rename(self):
        if not self._menu_targets or len(self._menu_targets) > 1:
            return
        InlineRename(self.sidebar, self._menu_targets[0], self._on_rename_success)

    def _copy_relative_path(self):
        if not self._menu_targets:
            return
        ctx = AppContext()
        root = ctx.project_root or ""
        paths = "\n".join([os.path.relpath(t, root) if root else t for t in self._menu_targets])
        self.sidebar.clipboard_clear()
        self.sidebar.clipboard_append(paths)

    def _copy_absolute_path(self):
        if not self._menu_targets:
            return
        paths = "\n".join(self._menu_targets)
        self.sidebar.clipboard_clear()
        self.sidebar.clipboard_append(paths)

    def _menu_delete(self):
        if not self._menu_targets:
            return
        count = len(self._menu_targets)
        name = os.path.basename(self._menu_targets[0]) if count == 1 else f"{count} itens"
        
        dialog = ctk.CTkToplevel(self.sidebar)
        dialog.title("Excluir")
        dialog.attributes("-topmost", True)
        dialog.update_idletasks()
        master = self.sidebar.winfo_toplevel()
        dialog.transient(master)
        dialog.resizable(False, False)
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = max(0, (screen_width // 2) - 175)
        y = max(0, (screen_height // 2) - 70)
        dialog.geometry(f"350x140+{x}+{y}")
        ctk.CTkLabel(dialog, text=f"Deseja excluir '{name}'?", pady=20).pack()
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()
        
        def do_delete():
            for target in self._menu_targets:
                if not FileManager.delete_path(target):
                    if hasattr(self.sidebar, "_show_error"):
                        self.sidebar._show_error(f"Não foi possível excluir o item: {os.path.basename(target)}")
            self.sidebar.refresh_explorer()
            dialog.destroy()
            
        ctk.CTkButton(btn_frame, text="Excluir", fg_color="#e06c75", hover_color="#be5046", command=do_delete).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)

    def _git_add(self):
        ctx = AppContext()
        if ctx.git_plugin and self._menu_targets:
            for t in self._menu_targets:
                ctx.git_plugin.stage_file(t)

    def _git_reset(self):
        ctx = AppContext()
        if ctx.git_plugin and self._menu_targets:
            for t in self._menu_targets:
                ctx.git_plugin.unstage_file(t)

    def _git_diff(self):
        ctx = AppContext()
        if not ctx.git_plugin or not self._menu_targets:
            return
        
        for t in self._menu_targets:
            diff_text = ctx.git_plugin.get_diff(t)
            if not diff_text:
                diff_text = "Nenhuma alteração detectada ou arquivo não rastreado."
            dialog = ctk.CTkToplevel(self.sidebar)
            dialog.title(f"Git Diff - {os.path.basename(t)}")
            dialog.geometry("700x500")
            txt = ctk.CTkTextbox(dialog, font=("Consolas", 11))
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt._textbox.tag_configure("add", foreground="#98c379")
            txt._textbox.tag_configure("del", foreground="#e06c75")
            txt._textbox.tag_configure("header", foreground="#61afef")
            for line in diff_text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    txt._textbox.insert("end", line + "\n", "add")
                elif line.startswith("-") and not line.startswith("---"):
                    txt._textbox.insert("end", line + "\n", "del")
                elif line.startswith("@@") or line.startswith("diff"):
                    txt._textbox.insert("end", line + "\n", "header")
                else:
                    txt._textbox.insert("end", line + "\n")
            txt.configure(state="disabled")

    def _on_rename_success(self, old_path, new_path):
        ctx = AppContext()
        if hasattr(ctx, "project_root") and ctx.project_root == old_path:
            ctx.project_root = new_path
        if hasattr(ctx, "tab_manager") and ctx.tab_manager:
            for tab in ctx.tab_manager.get_tabs():
                if not tab.path:
                    continue
                if tab.path == old_path:
                    ctx.tab_manager.update_tab_path(tab.id, new_path)
                elif tab.path.startswith(old_path + os.sep):
                    updated = new_path + tab.path[len(old_path):]
                    ctx.tab_manager.update_tab_path(tab.id, updated)
        if hasattr(ctx, "current_file") and ctx.current_file:
            if ctx.current_file == old_path:
                ctx.current_file = new_path
            elif ctx.current_file.startswith(old_path + os.sep):
                ctx.current_file = new_path + ctx.current_file[len(old_path):]
        if hasattr(ctx, "status_bar") and ctx.status_bar:
            ctx.status_bar.update_status(1, 0, ctx.current_file or new_path)
        if hasattr(ctx, "tab_bridge") and ctx.tab_bridge:
            ctx.tab_bridge._render_tabs()
        self.sidebar.refresh_explorer()