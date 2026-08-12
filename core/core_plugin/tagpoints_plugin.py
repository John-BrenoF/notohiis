import os
import json
import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any, Optional
from core.src.app_context import AppContext


class TagPointsPlugin:

    def __init__(self):
        self.ctx: Optional[AppContext] = None
        self.data: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = ""
        self.cache_file = ""
        self.colors = {
            "Vermelho": "#ff3b3b",
            "Verde": "#2ed573",
            "Azul": "#1e90ff",
            "Amarelo": "#ffd32a",
            "Roxo": "#a55eea",
            "Laranja": "#ff8f1f",
            "Ciano": "#17c9e0",
            "Rosa": "#ff2d95"
        }

    def setup(self, ctx: AppContext):
        self.ctx = ctx

        core_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = os.path.join(core_path, "cacheuser")
        self.cache_file = os.path.join(self.cache_dir, "tags.json")

        self._init_storage()
        self._setup_gitignore(os.path.dirname(core_path))

        if self.ctx.window:
            self.ctx.window.after(200, self._bind_events)

    def _norm_path(self, path: Optional[str]) -> str:
        if not path:
            return ""
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))

    def _init_storage(self):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            pass

        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                try:
                    backup_path = self.cache_file + ".corrupted"
                    os.replace(self.cache_file, backup_path)
                except Exception:
                    pass
                self.data = {}

    def _save_data(self):
        try:
            tmp_path = self.cache_file + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.cache_file)
        except Exception:
            pass

    def _setup_gitignore(self, root_path: str):
        gitignore_path = os.path.join(root_path, ".gitignore")
        entry = "core/cacheuser/tags.json"

        try:
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(f"{entry}\n")
                return

            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]

            if entry not in lines:
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    f.write(f"\n{entry}\n")
        except Exception:
            pass

    def _bind_events(self):
        if not self.ctx.editor:
            if self.ctx.window:
                self.ctx.window.after(200, self._bind_events)
            return

        editor = self.ctx.editor
        text_widget = self._get_text_widget()

        if text_widget is not None:
            text_widget.bind("<Button-3>", self._on_text_right_click, add="+")
            text_widget.bind("<Button-2>", self._on_text_right_click, add="+")

        if hasattr(editor, "line_numbers"):
            editor.line_numbers.bind("<Button-3>", self._on_canvas_right_click, add="+")
            editor.line_numbers.bind("<Button-2>", self._on_canvas_right_click, add="+")

        if hasattr(editor, "git_margin"):
            editor.git_margin.bind("<Button-3>", self._on_canvas_right_click, add="+")
            editor.git_margin.bind("<Button-2>", self._on_canvas_right_click, add="+")

        if hasattr(editor, "bind_key"):
            try:
                def navigate_down(event=None):
                    self._navigate(1)
                    return "break"

                def navigate_up(event=None):
                    self._navigate(-1)
                    return "break"

                editor.bind_key("<Control-Alt-Down>", navigate_down)
                editor.bind_key("<Control-Alt-Up>", navigate_up)
                if self.ctx.window is not None:
                    self.ctx.window.bind_all("<Control-Alt-Down>", navigate_down, add="+")
                    self.ctx.window.bind_all("<Control-Alt-Up>", navigate_up, add="+")
            except Exception:
                pass

        if hasattr(editor, "redraw_line_numbers"):
            original_redraw = editor.redraw_line_numbers

            def patched_redraw(*args, **kwargs):
                result = original_redraw(*args, **kwargs)
                self._draw_markers()
                return result

            editor.redraw_line_numbers = patched_redraw

        self._draw_markers()

    def _get_text_widget(self):
        editor = self.ctx.editor
        if not editor:
            return None

        textbox = getattr(editor, "textbox", None)
        if textbox is None:
            return None

        return getattr(textbox, "_textbox", textbox)

    def _resolve_line_from_event(self, event):
        text_widget = self._get_text_widget()
        if text_widget is None:
            return None

        try:
            if event.widget in (getattr(self.ctx.editor, "line_numbers", None), getattr(self.ctx.editor, "git_margin", None)):
                return self._line_from_canvas_y(event.y)

            if event.widget == text_widget or event.widget == getattr(self.ctx.editor, "textbox", None):
                return self._line_from_text_widget(text_widget, event.x, event.y)

            current = event.widget
            while current is not None:
                if current == text_widget or current == getattr(self.ctx.editor, "textbox", None):
                    return self._line_from_text_widget(text_widget, event.x, event.y)
                current = getattr(current, "master", None)
        except Exception:
            pass

        return None

    def _line_from_text_widget(self, text_widget, x, y):
        try:
            index = text_widget.index(f"@{x},{y}")
            return int(str(index).split(".")[0])
        except Exception:
            return None

    def _line_from_canvas_y(self, y):
        text_widget = self._get_text_widget()
        if text_widget is None:
            return None

        try:
            top_index = text_widget.index("@0,0")
            current_line = int(str(top_index).split(".")[0])
        except Exception:
            return None

        offset_y = 0
        while True:
            try:
                dline = text_widget.dlineinfo(f"{current_line}.0")
                if dline is None:
                    break
                height = dline[3] if len(dline) >= 4 else 1
                if offset_y <= y < offset_y + height:
                    return current_line
                offset_y += height
                current_line += 1
            except Exception:
                break

        return None

    def _on_canvas_right_click(self, event):
        line = self._resolve_line_from_event(event) or self._get_cursor_line()
        self._show_context_menu(event, line)
        return "break"

    def _on_text_right_click(self, event):
        line = self._resolve_line_from_event(event) or self._get_cursor_line()
        self._show_context_menu(event, line)
        return "break"

    def _get_cursor_line(self):
        try:
            index = self.ctx.editor.get_cursor_index()
            return int(str(index).split(".")[0])
        except Exception:
            return 1

    def _get_mouse_position(self):
        try:
            if self.ctx.window:
                return self.ctx.window.winfo_pointerx(), self.ctx.window.winfo_pointery()
        except Exception:
            pass
        return getattr(self, "_last_click_pos", (None, None))

    def _close_active_menu(self):
        active = getattr(self, "_active_menu", None)
        if active is not None:
            try:
                if active.winfo_exists():
                    active.destroy()
            except Exception:
                pass
            self._active_menu = None

    def _show_context_menu(self, event, line: int):
        if not self.ctx.window:
            return

        self._last_click_pos = (event.x_root, event.y_root)
        self._close_active_menu()

        path_key = self._norm_path(self.ctx.current_file)
        tags = self.data.get(path_key, {})
        line_key = str(line)
        has_tag = line_key in tags

        menu = ctk.CTkToplevel(self.ctx.window)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        try:
            menu.attributes("-alpha", 0.0)
        except Exception:
            pass

        self._active_menu = menu
        interactive_widgets = []

        card = ctk.CTkFrame(
            menu, corner_radius=8, border_width=1,
            border_color=("#d0d0d0", "#2a2c35"),
            fg_color=("#f5f5f5", "#16171d")
        )
        card.pack(fill="both", expand=True)

        def close_menu():
            try:
                if menu.winfo_exists():
                    menu.destroy()
            except Exception:
                pass
            if getattr(self, "_active_menu", None) is menu:
                self._active_menu = None

        def reposition():
            if not menu.winfo_exists():
                return
            menu.update_idletasks()
            w = menu.winfo_reqwidth()
            h = menu.winfo_reqheight()
            screen_w = menu.winfo_screenwidth()
            screen_h = menu.winfo_screenheight()

            # Centralizado na tela (guardado para uso futuro, se quiser voltar a usar)
            # x = max(0, (screen_w - w) // 2)
            # y = max(0, (screen_h - h) // 2)

            mx, my = self._get_mouse_position()
            if mx is None:
                mx, my = screen_w // 2, screen_h // 2
            x = min(max(0, mx), max(0, screen_w - w - 10))
            y = min(max(0, my), max(0, screen_h - h - 10))
            menu.geometry(f"{w}x{h}+{x}+{y}")

        def run_and_close(command):
            def handler():
                close_menu()
                if command:
                    command()
            return handler

        def add_item(text, command=None, enabled=True, danger=False):
            btn = ctk.CTkButton(
                card, text=text, anchor="w",
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color=("#ececec", "#2d313c"),
                text_color=("#c0392b", "#e06c75") if danger else ("#2a2a2a", "#e6e6e6"),
                corner_radius=6, height=32, width=250,
                command=run_and_close(command) if enabled else None,
                state="normal" if enabled else "disabled"
            )
            btn.pack(padx=8, pady=2, fill="x")
            interactive_widgets.append(btn)
            return btn

        def add_separator():
            ctk.CTkFrame(card, height=1, fg_color=("#e2e2e2", "#3a3f4b")).pack(fill="x", padx=12, pady=6)

        def add_expandable(title):
            wrapper = ctk.CTkFrame(card, fg_color="transparent")
            wrapper.pack(fill="x", padx=8, pady=2)

            content = ctk.CTkFrame(wrapper, fg_color="transparent")
            state = {"open": False}

            def toggle():
                state["open"] = not state["open"]
                if state["open"]:
                    header_btn.configure(text=f"▾  {title}")
                    content.pack(fill="x", pady=(2, 4))
                else:
                    header_btn.configure(text=f"▸  {title}")
                    content.pack_forget()
                reposition()

            header_btn = ctk.CTkButton(
                wrapper, text=f"▸  {title}", anchor="w",
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color=("#ececec", "#2d313c"),
                text_color=("#2a2a2a", "#e6e6e6"),
                corner_radius=6, height=32, width=250,
                command=toggle
            )
            header_btn.pack(fill="x")
            interactive_widgets.append(header_btn)
            return content

        if has_tag:
            info = tags[line_key]
            alias = info.get("alias", "").strip()
            edit_label = f"Editar: {alias}" if alias else f"Editar Tag Point (Linha {line})"
            add_item(edit_label, command=lambda: self._show_tag_dialog(line))

            color_content = add_expandable("Alterar Cor")
            grid_row = None
            for idx, (color_name, color_hex) in enumerate(self.colors.items()):
                if idx % 4 == 0:
                    grid_row = ctk.CTkFrame(color_content, fg_color="transparent")
                    grid_row.pack(pady=2)
                swatch = ctk.CTkButton(
                    grid_row, text="", width=28, height=28, corner_radius=6,
                    fg_color=color_hex, hover_color=color_hex,
                    border_width=3 if color_hex == info.get("color") else 0,
                    border_color=("#2a2a2a", "#f2f2f2"),
                    command=run_and_close(lambda c=color_name: self._quick_set_color(line, c))
                )
                swatch.pack(side="left", padx=3)
                interactive_widgets.append(swatch)

            add_item("Remover Tag Point", command=lambda: self._remove_tag(line), danger=True)
        else:
            add_item(f"Adicionar Tag Point (Linha {line})", command=lambda: self._show_tag_dialog(line))

        if tags:
            threshold = 1 if has_tag else 0
            has_other_tags = len(tags) > threshold

            add_separator()
            add_item("Ir para próximo Tag Point  ·  Ctrl+Alt+↓", command=lambda: self._navigate(1), enabled=has_other_tags)
            add_item("Ir para Tag Point anterior  ·  Ctrl+Alt+↑", command=lambda: self._navigate(-1), enabled=has_other_tags)

            list_content = add_expandable(f"Listar Tag Points ({len(tags)})")
            for l_key in sorted(tags.keys(), key=lambda x: int(x)):
                l_info = tags[l_key]
                l_alias = l_info.get("alias", "").strip()
                entry_label = f"Linha {l_key} — {l_alias}" if l_alias else f"Linha {l_key}"
                item_btn = ctk.CTkButton(
                    list_content, text=entry_label, anchor="w",
                    font=("Segoe UI", 10),
                    fg_color="transparent",
                    hover_color=("#ececec", "#2d313c"),
                    text_color=l_info.get("color", self.colors["Vermelho"]),
                    corner_radius=6, height=28, width=230,
                    command=run_and_close(lambda l=int(l_key): self._goto_line(l))
                )
                item_btn.pack(padx=(18, 0), pady=1, fill="x")
                interactive_widgets.append(item_btn)

            add_separator()
            add_item(f"Remover todos os Tag Points ({len(tags)})", command=self._remove_all_tags_current_file, danger=True)

        def schedule_focus_check(event=None):
            menu.after(60, check_focus)

        def check_focus():
            if not menu.winfo_exists():
                return
            try:
                focused = menu.focus_get()
            except Exception:
                focused = None
            if focused is None:
                return
            try:
                if focused.winfo_toplevel() != menu:
                    close_menu()
            except Exception:
                pass

        for widget in interactive_widgets:
            widget.bind("<FocusOut>", schedule_focus_check, add="+")

        menu.bind("<Escape>", lambda e: close_menu())

        def reveal():
            if not menu.winfo_exists():
                return
            menu.update_idletasks()
            reposition()
            try:
                menu.attributes("-alpha", 0.97)
            except Exception:
                pass
            menu.focus_force()
            if interactive_widgets:
                interactive_widgets[0].focus_set()

        reposition()
        menu.after(30, reveal)

    def _quick_set_color(self, line: int, color_name: str):
        path_key = self._norm_path(self.ctx.current_file)
        if path_key not in self.data or str(line) not in self.data[path_key]:
            return

        self.data[path_key][str(line)]["color"] = self.colors.get(color_name, self.colors["Vermelho"])
        self._save_data()
        self._draw_markers()

    def _goto_line(self, line: int):
        try:
            self.ctx.editor.set_cursor(f"{line}.0")
            text_widget = self._get_text_widget()
            if text_widget is not None:
                text_widget.see(f"{line}.0")
                try:
                    total_lines = max(1, self.ctx.editor.get_line_count())
                    text_widget.yview_moveto(max(0.0, (line - 3) / total_lines))
                except Exception:
                    pass
            self._draw_markers()
        except Exception:
            pass

    def _show_tag_dialog(self, line: int):
        if not self.ctx.window or not self.ctx.current_file:
            return

        path_key = self._norm_path(self.ctx.current_file)
        existing = self.data.get(path_key, {}).get(str(line), {})

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.overrideredirect(True)
        dialog.attributes("-topmost", True)
        try:
            dialog.attributes("-alpha", 0.0)
        except Exception:
            pass

        card = ctk.CTkFrame(
            dialog, corner_radius=8, border_width=1,
            border_color=("#d0d0d0", "#2a2c35"),
            fg_color=("#f5f5f5", "#16171d")
        )
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            card, text=f"Tag Point · Linha {line}",
            font=("Segoe UI", 12, "bold"),
            text_color=("#2a2a2a", "#e6e6e6")
        ).pack(pady=(16, 10), padx=18, anchor="w")

        ctk.CTkLabel(
            card, text="ALIAS", font=("Segoe UI", 9, "bold"),
            text_color=("#8a8a8a", "#8f96a3"), anchor="w"
        ).pack(fill="x", padx=18)
        alias_entry = ctk.CTkEntry(
            card, width=260, height=34, corner_radius=6,
            border_width=1, border_color=("#d5d5d5", "#3a3f4b"),
            fg_color=("#ffffff", "#1b1d24"),
            placeholder_text="Nome da marcação"
        )
        alias_entry.insert(0, existing.get("alias", ""))
        alias_entry.pack(padx=18, pady=(3, 12))

        ctk.CTkLabel(
            card, text="DESCRIÇÃO", font=("Segoe UI", 9, "bold"),
            text_color=("#8a8a8a", "#8f96a3"), anchor="w"
        ).pack(fill="x", padx=18)
        desc_entry = ctk.CTkEntry(
            card, width=260, height=34, corner_radius=6,
            border_width=1, border_color=("#d5d5d5", "#3a3f4b"),
            fg_color=("#ffffff", "#1b1d24"),
            placeholder_text="Descrição breve (opcional)"
        )
        desc_entry.insert(0, existing.get("desc", ""))
        desc_entry.pack(padx=18, pady=(3, 12))

        ctk.CTkLabel(
            card, text="COR", font=("Segoe UI", 9, "bold"),
            text_color=("#8a8a8a", "#8f96a3"), anchor="w"
        ).pack(fill="x", padx=18)

        current_color = existing.get("color", self.colors["Vermelho"])
        selected_color = tk.StringVar(value=current_color)
        swatch_buttons: Dict[str, ctk.CTkButton] = {}

        def select_color(color_hex):
            selected_color.set(color_hex)
            for c_hex, btn in swatch_buttons.items():
                btn.configure(border_width=3 if c_hex == color_hex else 0)

        swatch_wrap = ctk.CTkFrame(card, fg_color="transparent")
        swatch_wrap.pack(padx=16, pady=(4, 14), anchor="w")

        color_values = list(self.colors.values())
        per_row = 4
        for row_start in range(0, len(color_values), per_row):
            swatch_row = ctk.CTkFrame(swatch_wrap, fg_color="transparent")
            swatch_row.pack(pady=3)
            for color_hex in color_values[row_start:row_start + per_row]:
                btn = ctk.CTkButton(
                    swatch_row, text="", width=28, height=28, corner_radius=6,
                    fg_color=color_hex, hover_color=color_hex,
                    border_color=("#2a2a2a", "#f2f2f2"),
                    command=lambda c=color_hex: select_color(c)
                )
                btn.pack(side="left", padx=3)
                swatch_buttons[color_hex] = btn

        select_color(current_color)

        button_row = ctk.CTkFrame(card, fg_color="transparent")
        button_row.pack(padx=18, pady=(0, 18), fill="x")

        def close_dialog():
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except Exception:
                pass

        def save_tag(event=None):
            if path_key not in self.data:
                self.data[path_key] = {}

            self.data[path_key][str(line)] = {
                "alias": alias_entry.get().strip(),
                "desc": desc_entry.get().strip(),
                "color": selected_color.get()
            }
            self._save_data()
            self._draw_markers()
            close_dialog()

        cancel_btn = ctk.CTkButton(
            button_row, text="Cancelar", command=close_dialog, width=118, height=34,
            corner_radius=6,
            fg_color="transparent", border_width=1,
            border_color=("#c0c0c0", "#555555"),
            text_color=("#444444", "#cfcfcf"),
            hover_color=("#ececec", "#31343f")
        )
        cancel_btn.pack(side="left")

        confirm_btn = ctk.CTkButton(
            button_row, text="Confirmar", command=save_tag, width=118, height=34,
            corner_radius=6,
            fg_color="#4d9fe0", hover_color="#3f8cc9"
        )
        confirm_btn.pack(side="right")

        dialog.bind("<Return>", save_tag)
        dialog.bind("<Escape>", lambda e: close_dialog())

        def schedule_focus_check(event=None):
            dialog.after(60, check_focus)

        def check_focus():
            if not dialog.winfo_exists():
                return
            try:
                focused = dialog.focus_get()
            except Exception:
                focused = None
            if focused is None:
                return
            try:
                if focused.winfo_toplevel() != dialog:
                    close_dialog()
            except Exception:
                pass

        for widget in (alias_entry, desc_entry, cancel_btn, confirm_btn, *swatch_buttons.values()):
            widget.bind("<FocusOut>", schedule_focus_check, add="+")

        def position_dialog():
            dialog.update_idletasks()
            w = dialog.winfo_reqwidth()
            h = dialog.winfo_reqheight()
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()

            # Centralizado na tela (guardado para uso futuro, se quiser voltar a usar)
            # x = max(0, (screen_w - w) // 2)
            # y = max(0, (screen_h - h) // 2)

            mx, my = self._get_mouse_position()
            if mx is None:
                mx, my = screen_w // 2, screen_h // 2
            x = min(max(0, mx), max(0, screen_w - w - 10))
            y = min(max(0, my), max(0, screen_h - h - 10))
            dialog.geometry(f"{w}x{h}+{x}+{y}")

        def reveal():
            if not dialog.winfo_exists():
                return
            position_dialog()
            try:
                dialog.attributes("-alpha", 0.96)
            except Exception:
                pass
            dialog.focus_force()
            alias_entry.focus_set()

        position_dialog()
        dialog.after(30, reveal)

    def _remove_tag(self, line: int):
        path_key = self._norm_path(self.ctx.current_file)
        if not path_key:
            return

        if path_key in self.data and str(line) in self.data[path_key]:
            del self.data[path_key][str(line)]
            if not self.data[path_key]:
                del self.data[path_key]
            self._save_data()
            self._draw_markers()

    def _remove_all_tags_current_file(self):
        path_key = self._norm_path(self.ctx.current_file)
        if not path_key or path_key not in self.data:
            return

        del self.data[path_key]
        self._save_data()
        self._draw_markers()

    def _draw_markers(self):
        editor = self.ctx.editor
        if not editor or not hasattr(editor, "git_margin") or not self.ctx.current_file:
            return

        try:
            editor.git_margin.delete("tag_point")
        except Exception:
            pass

        path_key = self._norm_path(self.ctx.current_file)
        tags = self.data.get(path_key, {})
        if not tags:
            return

        text_widget = self._get_text_widget()
        if text_widget is None:
            return

        for line_key, info in tags.items():
            try:
                dline = text_widget.dlineinfo(f"{line_key}.0")
                if not dline:
                    continue
                y = dline[1]
                editor.git_margin.create_oval(
                    2, y + 2, 12, y + 12,
                    fill=info.get("color", self.colors["Vermelho"]),
                    outline="",
                    tags="tag_point"
                )
            except Exception:
                continue

    def _navigate(self, direction: int):
        path_key = self._norm_path(self.ctx.current_file)
        if not path_key or path_key not in self.data:
            return

        lines = []
        for key in self.data[path_key].keys():
            try:
                lines.append(int(key))
            except (TypeError, ValueError):
                continue
        lines.sort()

        if not lines:
            return

        current_line = self._get_cursor_line()
        if direction > 0:
            target_line = next((line for line in lines if line > current_line), lines[0])
        else:
            target_line = next((line for line in reversed(lines) if line < current_line), lines[-1])

        self._goto_line(target_line)

    def run(self):
        self._draw_markers()


def setup(ctx):
    plugin = TagPointsPlugin()
    plugin.setup(ctx)
    if hasattr(ctx, "external_plugins"):
        ctx.external_plugins.append(plugin)