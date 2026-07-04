import os
import tkinter as tk
import customtkinter as ctk
from core.src.file_manager import FileManager
from core.src.app_context import AppContext


class RenameDialog:
    def __init__(self, parent, target_path, on_confirm):
        self.parent = parent
        self.target_path = target_path
        self.on_confirm = on_confirm
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Renomear")
        self.dialog.attributes("-topmost", True)
        self._center_dialog(350, 160)
        ctk.CTkLabel(self.dialog, text=f"Novo nome para '{os.path.basename(target_path)}':", pady=10).pack()
        self.entry = ctk.CTkEntry(self.dialog, width=280)
        self.entry.insert(0, os.path.basename(target_path))
        self.entry.pack(pady=10)
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)
        buttons = ctk.CTkFrame(self.dialog, fg_color="transparent")
        buttons.pack()
        ctk.CTkButton(buttons, text="Renomear", command=self._confirm).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Cancelar", fg_color="gray", command=self.dialog.destroy).pack(side="left", padx=6)
        self.entry.bind("<Return>", self._confirm)
        self.entry.bind("<Escape>", lambda e: self.dialog.destroy())

    def _center_dialog(self, width, height):
        self.dialog.update_idletasks()
        master = self.parent.winfo_toplevel()
        self.dialog.transient(master)
        self.dialog.resizable(False, False)
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, (screen_width // 2) - (width // 2))
        y = max(0, (screen_height // 2) - (height // 2))
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _confirm(self, event=None):
        new_name = self.entry.get().strip()
        if not new_name:
            self.dialog.destroy()
            return
        if new_name == os.path.basename(self.target_path):
            self.dialog.destroy()
            return
        if FileManager.rename_path(self.target_path, new_name):
            new_path = os.path.join(os.path.dirname(self.target_path), new_name)
            self.on_confirm(self.target_path, new_path)
        else:
            if hasattr(self.parent, "_show_error"):
                self.parent._show_error("Não foi possível renomear o item.")
        self.dialog.destroy()


class SidebarContextMenu:
    def __init__(self, sidebar):
        self.sidebar = sidebar
        self.popup = None
        self.theme = AppContext().theme.get("sidebar", {})
        self._menu_target = None
        self._unbind_id = None

    def show(self, event, target_path=None):
        self._menu_target = target_path
        self._close_menu()
        menu_bg = self.theme.get("menu_bg", "#282c34")
        border = self.theme.get("menu_border", "#3e4451")
        width = 240
        self.popup = ctk.CTkToplevel(self.sidebar)
        self.popup.overrideredirect(True)
        self.popup.lift()
        self.popup.wm_attributes("-topmost", True)
        self.popup.configure(fg_color=menu_bg, border_width=1, border_color=border)
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

    def _build_menu(self):
        label_style = {
            "text_color": self.theme.get("menu_heading", "#8f9bb3"),
            "font": ("Segoe UI", 9, "bold")
        }
        base_style = {
            "fg_color": self.theme.get("menu_item_bg", "#323842"),
            "hover_color": self.theme.get("menu_item_hover", "#3f4b61"),
            "text_color": self.theme.get("menu_fg", "#dcdfe4"),
            "corner_radius": 8,
            "height": 34,
            "border_width": 0,
            "anchor": "w"
        }
        
        self._add_item("Novo Arquivo", self._menu_new_file, icon="\uf15b", **base_style)
        self._add_item("Nova Pasta", self._menu_new_folder, icon="\uf07b", **base_style)
        self._add_item("Renomear", self._menu_rename, icon="\uf044", **base_style, state="normal" if self._menu_target else "disabled")
        self._add_separator()
        delete_style = base_style.copy()
        delete_style["fg_color"] = "#3f1f28"
        delete_style["hover_color"] = "#5c2b39"
        self._add_item("Excluir", self._menu_delete, icon="\uf1f8", **delete_style)
        self._add_separator()
        ctk.CTkLabel(self.popup, text="Git", **label_style).pack(fill="x", padx=14, pady=(6, 2))
        self._add_item("Add (Stage)", self._git_add, icon="\uf067", **base_style, state="normal" if self._menu_target else "disabled")
        self._add_item("Reset (Unstage)", self._git_reset, icon="\uf0e2", **base_style, state="normal" if self._menu_target else "disabled")
        self._add_item("Ver Diff", self._git_diff, icon="\uf126", **base_style, state="normal" if self._menu_target else "disabled")
        
    def _add_item(self, label, command, icon="", **kwargs):
        btn = ctk.CTkButton(self.popup, text=f"{icon}    {label}", command=lambda: self._action(command), **kwargs)
        btn.pack(fill="x", padx=10, pady=4)
        btn.bind("<Button-1>", lambda e: self._action(command))

    def _add_separator(self):
        sep = ctk.CTkFrame(self.popup, height=1, fg_color=self.theme.get("menu_separator", "#3e4451"))
        sep.pack(fill="x", padx=10, pady=6)

    def _action(self, command):
        self._close_menu()
        command()

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
        self.sidebar._show_inline_entry(is_dir=False, target_path=self._menu_target)

    def _menu_new_folder(self):
        self.sidebar._show_inline_entry(is_dir=True, target_path=self._menu_target)

    def _menu_rename(self):
        if not self._menu_target:
            return
        RenameDialog(self.sidebar, self._menu_target, self._on_rename_success)

    def _menu_delete(self):
        if not self._menu_target:
            return
        name = os.path.basename(self._menu_target)
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
            if FileManager.delete_path(self._menu_target):
                self.sidebar.refresh_explorer()
            else:
                if hasattr(self.sidebar, "_show_error"):
                    self.sidebar._show_error("Não foi possível excluir o item.")
            dialog.destroy()
        ctk.CTkButton(btn_frame, text="Excluir", fg_color="#e06c75", hover_color="#be5046", command=do_delete).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)

    def _git_add(self):
        ctx = AppContext()
        if ctx.git_plugin and self._menu_target:
            ctx.git_plugin.stage_file(self._menu_target)

    def _git_reset(self):
        ctx = AppContext()
        if ctx.git_plugin and self._menu_target:
            ctx.git_plugin.unstage_file(self._menu_target)

    def _git_diff(self):
        ctx = AppContext()
        if not ctx.git_plugin or not self._menu_target:
            return
        diff_text = ctx.git_plugin.get_diff(self._menu_target)
        if not diff_text:
            diff_text = "Nenhuma alteração detectada ou arquivo não rastreado."
        dialog = ctk.CTkToplevel(self.sidebar)
        dialog.title(f"Git Diff - {os.path.basename(self._menu_target)}")
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
