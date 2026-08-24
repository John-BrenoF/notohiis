import os
import customtkinter as ctk
from core.src.app_context import AppContext
from core.core_plugin.global_search_engine import SearchMatch


class GlobalSearchPanel(ctk.CTkFrame):
    """Painel de resultados da busca global no sidebar."""

    MAX_VISIBLE_RESULTS = 200

    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self.ctx = AppContext()
        self._result_buttons = []

        self._build_header()
        self._build_scrollable_results()

    def _build_header(self):
        theme = self.ctx.theme.get("sidebar", {})
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(10, 6), padx=10)

        ctk.CTkLabel(
            header, text="BUSCA GLOBAL", font=("Segoe UI", 10, "bold"),
            text_color=theme.get("label", "gray")
        ).pack(side="left")

        self._close_btn = ctk.CTkButton(
            header, text="󰅖", width=24, height=24, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), font=("Segoe UI", 14),
            command=self._on_close
        )
        self._close_btn.pack(side="right")

        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(0, 6))

        self._search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Buscar termo...", height=28,
            font=("Segoe UI", 11), border_width=1,
            border_color=theme.get("hover", "#2d2d2d"),
            fg_color=theme.get("bg", "#1a1a1c"),
            text_color=theme.get("fg", "#cccccc")
        )
        self._search_entry.pack(fill="x")
        self._search_entry.bind("<KeyRelease>", self._on_search_type)

        self._status_label = ctk.CTkLabel(
            search_frame, text="", font=("Segoe UI", 9),
            text_color=theme.get("label", "gray")
        )
        self._status_label.pack(anchor="w", pady=(2, 0))

    def _build_scrollable_results(self):
        theme = self.ctx.theme.get("sidebar", {})
        self._scroll_frame = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370")
        )
        self._scroll_frame.pack(fill="both", expand=True)
        self._scroll_frame._scrollbar.configure(width=6)

    def _on_search_type(self, event):
        if event.keysym in ("Return", "Escape", "Up", "Down", "Left", "Right"):
            return
        term = self._search_entry.get().strip()
        if not term:
            self._clear_results()
            self._status_label.configure(text="")
            return
        self._execute_search(term)

    def _execute_search(self, term: str):
        engine = getattr(self.ctx, 'global_search_engine', None)
        if not engine or not self.ctx.project_root:
            self._status_label.configure(text="Motor de busca indisponível")
            return

        results = engine.search(term, self.ctx.project_root)
        self._render_results(results, term)

    def _render_results(self, results: list, term: str):
        self._clear_results()
        theme = self.ctx.theme.get("sidebar", {})

        if not results:
            self._status_label.configure(text="Nenhum resultado encontrado")
            return

        total = len(results)
        shown = min(total, self.MAX_VISIBLE_RESULTS)
        self._status_label.configure(text=f"{total} resultado{'s' if total != 1 else ''}")

        grouped = self._group_results_by_file(results)

        for file_path, file_results in grouped.items():
            self._add_file_header(file_path, theme)
            for match in file_results[:50]:
                self._add_result_item(match, term, theme)

        if total > shown:
            ctk.CTkLabel(
                self._scroll_frame,
                text=f"... +{total - shown} resultados não exibidos",
                font=("Segoe UI", 9), text_color=theme.get("label", "gray")
            ).pack(pady=4)

    def _group_results_by_file(self, results: list) -> dict:
        grouped = {}
        for match in results:
            if match.file_path not in grouped:
                grouped[match.file_path] = []
            grouped[match.file_path].append(match)
        return grouped

    def _add_file_header(self, file_path: str, theme: dict):
        rel_path = self._relative_path(file_path)
        header = ctk.CTkButton(
            self._scroll_frame, text=f" 󰈔 {rel_path}", anchor="w",
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            text_color=theme.get("label", "gray"),
            hover_color=theme.get("hover", "#2d2d2d"),
            height=24, corner_radius=4,
            command=lambda p=file_path: self._open_file(p, 1)
        )
        header.pack(fill="x", padx=4, pady=(6, 1))

    def _add_result_item(self, match: SearchMatch, term: str, theme: dict):
        display_text = match.line_text.strip()
        if len(display_text) > 80:
            display_text = display_text[:80] + "..."

        btn = ctk.CTkButton(
            self._scroll_frame,
            text=f"  {match.line_number}: {display_text}",
            anchor="w", font=("Consolas", 10),
            fg_color="transparent",
            text_color=theme.get("fg", "#cccccc"),
            hover_color=theme.get("selected", "#3a3f4b"),
            height=22, corner_radius=3,
            command=lambda p=match.file_path, l=match.line_number: self._open_file(p, l)
        )
        btn.pack(fill="x", padx=8, pady=1)
        self._result_buttons.append(btn)

    def _open_file(self, file_path: str, line_number: int):
        ctx = self.ctx
        if hasattr(ctx, 'tab_bridge') and ctx.tab_bridge:
            ctx.tab_bridge.open_file(file_path)
        else:
            ctx.current_file = file_path
            ctx.is_dirty = False
            from core.src.buffer import BufferManager
            content = BufferManager.read_file(file_path)
            if ctx.editor:
                ctx.editor.set_text(content)

        if ctx.editor:
            ctx.editor.set_cursor(f"{line_number}.0")
            text_widget = self._get_text_widget()
            if text_widget:
                text_widget.see(f"{line_number}.0")

        if ctx.status_bar:
            ctx.status_bar.update_status(line_number, 0, file_path)

    def _get_text_widget(self):
        editor = self.ctx.editor
        if not editor:
            return None
        textbox = getattr(editor, "textbox", None)
        if textbox is None:
            return None
        return getattr(textbox, "_textbox", textbox)

    def _relative_path(self, file_path: str) -> str:
        root = self.ctx.project_root
        if root and file_path.startswith(root):
            return file_path[len(root):].lstrip(os.sep)
        return file_path

    def _clear_results(self):
        for btn in self._result_buttons:
            btn.destroy()
        self._result_buttons.clear()
        for child in self._scroll_frame.winfo_children():
            child.destroy()

    def _on_close(self):
        if hasattr(self, '_on_close_callback') and self._on_close_callback:
            self._on_close_callback()

    def set_close_callback(self, callback):
        self._on_close_callback = callback

    def focus_search(self):
        self._search_entry.focus_set()

    def apply_theme(self):
        theme = self.ctx.theme.get("sidebar", {})
        self.configure(fg_color=theme.get("bg", "#1a1a1c"))
        self._search_entry.configure(
            border_color=theme.get("hover", "#2d2d2d"),
            fg_color=theme.get("bg", "#1a1a1c"),
            text_color=theme.get("fg", "#cccccc")
        )
        self._status_label.configure(text_color=theme.get("label", "gray"))
        self._close_btn.configure(
            hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray")
        )
        self._scroll_frame.configure(
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370")
        )
