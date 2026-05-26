import os
import json
import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any, Optional
from core.src.app_context import AppContext

class TagPointsPlugin:
    """
    Gerencia pontos de marcação (Tag Points) em linhas específicas.
    Permite navegação rápida e persistência de anotações por arquivo.
    """

    def __init__(self):
        self.ctx: Optional[AppContext] = None
        self.data: Dict[str, Dict[str, Any]] = {}
        self.cache_dir = ""
        self.cache_file = ""
        self.colors = {
            "Vermelho": "#e06c75",
            "Verde": "#98c379",
            "Azul": "#61afef",
            "Amarelo": "#e5c07b"
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
                self.data = {}

    def _save_data(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
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

    def _show_context_menu(self, event, line: int):
        if not self.ctx.window:
            return

        menu = tk.Menu(self.ctx.window, tearoff=0)
        tags = self.data.get(self.ctx.current_file or "", {})
        line_key = str(line)

        if line_key in tags:
            menu.add_command(label=f"Editar Tag Point (Linha {line})", command=lambda: self._show_tag_dialog(line))
            menu.add_command(label="Remover Tag Point", command=lambda: self._remove_tag(line))
        else:
            menu.add_command(label=f"Adicionar Tag Point (Linha {line})", command=lambda: self._show_tag_dialog(line))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _show_tag_dialog(self, line: int):
        if not self.ctx.window or not self.ctx.current_file:
            return

        path = self.ctx.current_file
        existing = self.data.get(path, {}).get(str(line), {})

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.title(f"Tag Point - Linha {line}")
        dialog.geometry("320x320")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Alias / Nome:", font=("Segoe UI", 11, "bold")).pack(pady=(20, 0))
        alias_entry = ctk.CTkEntry(dialog, width=250)
        alias_entry.insert(0, existing.get("alias", ""))
        alias_entry.pack(pady=5)

        ctk.CTkLabel(dialog, text="Descrição breve:").pack(pady=(5, 0))
        desc_entry = ctk.CTkEntry(dialog, width=250)
        desc_entry.insert(0, existing.get("desc", ""))
        desc_entry.pack(pady=5)

        current_color = existing.get("color", self.colors["Vermelho"])
        current_name = next((name for name, value in self.colors.items() if value == current_color), "Vermelho")

        color_var = tk.StringVar(value=current_name)
        ctk.CTkOptionMenu(dialog, values=list(self.colors.keys()), variable=color_var, width=250).pack(pady=15)

        def save_tag():
            if path not in self.data:
                self.data[path] = {}

            self.data[path][str(line)] = {
                "alias": alias_entry.get().strip(),
                "desc": desc_entry.get().strip(),
                "color": self.colors.get(color_var.get(), self.colors["Vermelho"])
            }
            self._save_data()
            self._draw_markers()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Confirmar", command=save_tag, width=250, fg_color="#4d9fe0").pack(pady=10)

    def _remove_tag(self, line: int):
        path = self.ctx.current_file
        if not path:
            return

        if path in self.data and str(line) in self.data[path]:
            del self.data[path][str(line)]
            if not self.data[path]:
                del self.data[path]
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

        tags = self.data.get(self.ctx.current_file, {})
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
        path = self.ctx.current_file
        if not path or path not in self.data:
            return

        try:
            lines = sorted(int(line) for line in self.data[path].keys())
        except Exception:
            return

        if not lines:
            return

        current_line = self._get_cursor_line()
        if direction > 0:
            target_line = next((line for line in lines if line > current_line), lines[0])
        else:
            target_line = next((line for line in reversed(lines) if line < current_line), lines[-1])

        try:
            self.ctx.editor.set_cursor(f"{target_line}.0")
            text_widget = self._get_text_widget()
            if text_widget is not None:
                text_widget.see(f"{target_line}.0")
                try:
                    # Tenta centralizar a linha no viewport, se disponível.
                    text_widget.yview_moveto(max(0.0, (target_line - 3) / max(1, self.ctx.editor.get_line_count())))
                except Exception:
                    pass
            self._draw_markers()
        except Exception:
            pass

    def run(self):
        self._draw_markers()


def setup(ctx):
    plugin = TagPointsPlugin()
    plugin.setup(ctx)
    if hasattr(ctx, "external_plugins"):
        ctx.external_plugins.append(plugin)
