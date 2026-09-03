import customtkinter as ctk

from core.src.app_context import AppContext
from core.src.file_name_search import FileNameSearchResult, FileNameSearchService


class FileNameSearchPanel(ctk.CTkFrame):
    def __init__(self, master, on_open_result, on_close):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.context = AppContext()
        self.search_service = FileNameSearchService()
        self.on_open_result = on_open_result
        self.on_close = on_close
        self._search_generation = 0
        self._result_buttons = []
        self._build_widgets()

    def _build_widgets(self):
        theme = self.context.theme.get("sidebar", {})
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(
            header,
            text="ARQUIVOS E PASTAS",
            font=("Segoe UI", 10, "bold"),
            text_color=theme.get("label", "gray"),
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="×",
            width=24,
            height=24,
            corner_radius=4,
            fg_color="transparent",
            hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"),
            command=self.close,
        ).pack(side="right")

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Buscar pelo nome...",
            height=28,
            font=("Segoe UI", 11),
            border_color=theme.get("hover", "#2d2d2d"),
            fg_color=theme.get("bg", "#1a1a1c"),
            text_color=theme.get("fg", "#cccccc"),
        )
        self.search_entry.pack(fill="x", padx=10, pady=(0, 4))
        self.search_entry.bind("<KeyRelease>", self._on_query_changed)
        self.search_entry.bind("<Return>", self._open_first_result)
        self.search_entry.bind("<Escape>", lambda event: self.close())

        self.status_label = ctk.CTkLabel(
            self,
            text="Digite um nome",
            font=("Segoe UI", 9),
            text_color=theme.get("label", "gray"),
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=10, pady=(0, 6))

        self.results_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370"),
        )
        self.results_frame.pack(fill="both", expand=True)
        self.results_frame._scrollbar.configure(width=8)

    def open(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def close(self):
        self.search_service.cancel()
        self._search_generation += 1
        self.on_close()

    def clear_results(self):
        for button in self._result_buttons:
            button.destroy()
        self._result_buttons.clear()

    def apply_theme(self):
        theme = self.context.theme.get("sidebar", {})
        self.configure(fg_color="transparent")
        self.search_entry.configure(
            border_color=theme.get("hover", "#2d2d2d"),
            fg_color=theme.get("bg", "#1a1a1c"),
            text_color=theme.get("fg", "#cccccc"),
        )
        self.status_label.configure(text_color=theme.get("label", "gray"))
        self.results_frame.configure(
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370"),
        )

    def _on_query_changed(self, event=None):
        if event and event.keysym in ("Return", "Escape", "Up", "Down"):
            return
        query = self.search_entry.get()
        self._search_generation += 1
        generation = self._search_generation
        self.search_service.cancel()
        self.clear_results()
        if not query.strip():
            self.status_label.configure(text="Digite um nome")
            return

        self.status_label.configure(text="Buscando...")
        root_path = self.context.project_root
        self.search_service.search_async(
            query,
            root_path,
            lambda batch: self._show_result_batch(generation, batch),
            lambda total: self._finish_search(generation, total),
        )

    def _show_result_batch(self, generation, results):
        if generation != self._search_generation or not self.winfo_exists():
            return
        self.after(0, lambda: self._append_result_buttons(generation, results))

    def _append_result_buttons(self, generation, results):
        if generation != self._search_generation or not self.winfo_exists():
            return
        theme = self.context.theme.get("sidebar", {})
        for result in results:
            icon = "󰉋" if result.is_directory else "󰈔"
            button = ctk.CTkButton(
                self.results_frame,
                text=f"{icon}  {result.name}",
                anchor="w",
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color=theme.get("hover", "#2d2d2d"),
                text_color=theme.get("fg", "#cccccc"),
                height=26,
                corner_radius=4,
                command=lambda item=result: self.on_open_result(item),
            )
            button.pack(fill="x", padx=4, pady=1)
            self._result_buttons.append(button)

    def _finish_search(self, generation, total):
        if generation != self._search_generation or not self.winfo_exists():
            return
        self.after(0, lambda: self._update_search_status(generation, total))

    def _update_search_status(self, generation, total):
        if generation != self._search_generation or not self.winfo_exists():
            return
        if total == 0:
            self.status_label.configure(text="Nenhum resultado")
        else:
            self.status_label.configure(text=f"{total} resultado{'s' if total != 1 else ''}")

    def _open_first_result(self, event=None):
        if self._result_buttons:
            self._result_buttons[0].invoke()
        return "break"
