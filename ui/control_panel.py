import customtkinter as ctk
import os
import tkinter as tk
from core.src.app_context import AppContext
from core.src.buffer import BufferManager
try:
    from core.src.theme_manager import ThemeManager
except (ImportError, AttributeError):
    ThemeManager = None

class ControlPanel(ctk.CTkToplevel):
    """Painel central de controle para configurações e plugins."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Notohiis Control Panel")
        self.minsize(700, 520)
        self.attributes("-topmost", True)
        self.grab_set()

        self.ctx = AppContext()
        if ThemeManager:
            self.theme_options = ThemeManager.get_theme_display_list() or ["editor"]
        else:
            self.theme_options = ["Padrão (Sistema)"]
            
        self.selected_theme = self.ctx.selected_theme or self.theme_options[0]
        self._center_window(860, 640)

        self.configure(fg_color="#121216")
        self.resizable(True, True)

        # ── Layout raiz: sidebar + conteúdo ──────────────────────────────────
        self.grid_columnconfigure(0, weight=0)   # sidebar fixa
        self.grid_columnconfigure(1, weight=1)   # conteúdo expansível
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # ── Sidebar de navegação ─────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(
            self, fg_color="#0e0e12", corner_radius=0, width=180
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)  # empurra items para cima

        ctk.CTkLabel(
            self.sidebar,
            text="NOTOHIIS",
            font=("Segoe UI", 11, "bold"),
            text_color="#3d3f52",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(22, 18))

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._active_page = tk.StringVar(value="appearance")

        nav_items = [
            ("appearance", "󰔎  Aparência"),
            ("plugins",    "󰚥  Plugins"),
            ("about",      "󰋽  Sobre"),
        ]
        for idx, (key, label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=("Segoe UI", 13),
                fg_color="transparent",
                hover_color="#1e1f28",
                text_color="#a8a8b3",
                corner_radius=8,
                height=38,
                command=lambda k=key: self._switch_page(k),
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)
            self._nav_buttons[key] = btn

        # ── Área de conteúdo ─────────────────────────────────────────────────
        self.content_area = ctk.CTkFrame(self, fg_color="#121216", corner_radius=0)
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # ── Páginas ──────────────────────────────────────────────────────────
        self._build_appearance_page()
        self._build_plugins_page()
        self._build_about_page()

        # ── Rodapé ───────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="#0e0e12", corner_radius=0, height=32)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="ESC  fechar   •   ctrl+s  aplicar tema",
            font=("Segoe UI", 10),
            text_color="#3d3f52",
        ).grid(row=0, column=0, pady=6)

        self._switch_page("appearance")

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-s>", lambda e: self._apply_theme())

    # ─────────────────────────── navegação ───────────────────────────────────

    def _switch_page(self, key: str):
        for k, frame in self._pages.items():
            frame.grid_remove()
        self._pages[key].grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color="#1e1f28",
                    text_color="#ffffff",
                    font=("Segoe UI", 13, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#a8a8b3",
                    font=("Segoe UI", 13),
                )
        self._active_page.set(key)

    # ─────────────────────────── página: aparência ───────────────────────────

    def _build_appearance_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(3, weight=1)   # preview se expande
        self._pages["appearance"] = page

        # Título
        ctk.CTkLabel(
            page, text="Aparência",
            font=("Segoe UI", 22, "bold"), text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            page,
            text="Escolha um tema pronto ou edite diretamente o arquivo de estilo.",
            font=("Segoe UI", 11),
            text_color="#6b6f87",
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        # Seletor de tema
        selector_row = ctk.CTkFrame(page, fg_color="transparent")
        selector_row.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        selector_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector_row, text="Tema ativo",
            font=("Segoe UI", 12, "bold"), text_color="#c9ccd9"
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.theme_menu = ctk.CTkOptionMenu(
            selector_row,
            values=self.theme_options,
            command=self._on_theme_selected,
            corner_radius=10,
            fg_color="#1e1f28",
            button_color="#2b2d3a",
            button_hover_color="#383a47",
            text_color="#ffffff",
            dropdown_fg_color="#1e1f28",
            dropdown_hover_color="#2b2d3a",
            dropdown_text_color="#d3d5df",
        )
        self.theme_menu.grid(row=0, column=1, sticky="ew")
        self.theme_menu.set(self.selected_theme)

        # Preview expansível
        preview_card = ctk.CTkFrame(
            page, fg_color="#18181d",
            corner_radius=14, border_width=1, border_color="#2b2b35"
        )
        preview_card.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        # Topo do card
        top_bar = ctk.CTkFrame(preview_card, fg_color="#1e1f28", corner_radius=10)
        top_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        top_bar.grid_columnconfigure(0, weight=1)

        self.preview_title = ctk.CTkLabel(
            top_bar, text="Visualização do Tema",
            font=("Segoe UI", 12, "bold"), text_color="#c9ccd9"
        )
        self.preview_title.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        btn_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_row.grid(row=0, column=1, padx=14, pady=8)

        self.preview_button = ctk.CTkButton(
            btn_row,
            text="Aplicar",
            command=self._apply_theme,
            width=100,
            corner_radius=10,
            fg_color="#61afef",
            hover_color="#4d9fe0",
            text_color="#0f172a",
            font=("Segoe UI", 12, "bold"),
        )
        self.preview_button.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="Editar JSON",
            command=self._open_current_theme,
            width=100,
            corner_radius=10,
            fg_color="#2f2f3a",
            hover_color="#3a3b4d",
            text_color="#d3d5df",
        ).pack(side="left")

        # Swatches
        swatch_row = ctk.CTkFrame(preview_card, fg_color="transparent")
        swatch_row.grid(row=1, column=0, sticky="ew", padx=14, pady=14)
        swatch_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.bg_swatch     = self._build_swatch(swatch_row, "Fundo",    col=0)
        self.text_swatch   = self._build_swatch(swatch_row, "Texto",    col=1)
        self.accent_swatch = self._build_swatch(swatch_row, "Destaque", col=2)

        self._render_theme_preview(self.selected_theme)

    # ─────────────────────────── página: plugins ─────────────────────────────

    def _build_plugins_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        self._pages["plugins"] = page

        ctk.CTkLabel(
            page, text="Plugins Ativos",
            font=("Segoe UI", 22, "bold"), text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            page,
            text="Plugins carregados pelo sistema.",
            font=("Segoe UI", 11),
            text_color="#6b6f87",
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        # ScrollableFrame que usa todo o espaço disponível
        self.scroll_plugins = ctk.CTkScrollableFrame(
            page,
            fg_color="#18181d",
            corner_radius=14,
            border_width=1,
            border_color="#2b2b35",
            scrollbar_button_color="#2f2f3a",
            scrollbar_button_hover_color="#4f546c",
        )
        self.scroll_plugins.grid(row=2, column=0, sticky="nsew")
        self.scroll_plugins.grid_columnconfigure(0, weight=1)

        self._load_plugins()

    # ─────────────────────────── página: sobre ───────────────────────────────

    def _build_about_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        self._pages["about"] = page

        ctk.CTkLabel(
            page, text="Notohiis",
            font=("Segoe UI", 28, "bold"), text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            page,
            text="Editor de texto extensível com suporte a temas e plugins.",
            font=("Segoe UI", 12),
            text_color="#6b6f87",
        ).grid(row=1, column=0, sticky="w", pady=(0, 24))

        info_card = ctk.CTkFrame(
            page, fg_color="#18181d",
            corner_radius=14, border_width=1, border_color="#2b2b35"
        )
        info_card.grid(row=2, column=0, sticky="ew")
        info_card.grid_columnconfigure(1, weight=1)

        rows = [
            ("Versão",    "0.4-alpha (Batata estilosa) 🥔😎"),
            ("Licença",   "GPL-3.0"),
            ("feito por",    "John BrenoF"),
            ("UI Lib",    "CustomTkinter"),
        ]
        for i, (k, v) in enumerate(rows):
            ctk.CTkLabel(
                info_card, text=k,
                font=("Segoe UI", 11, "bold"), text_color="#6b6f87"
            ).grid(row=i, column=0, sticky="w", padx=20, pady=8)
            ctk.CTkLabel(
                info_card, text=v,
                font=("Segoe UI", 11), text_color="#d3d5df"
            ).grid(row=i, column=1, sticky="w", padx=12, pady=8)

    # ─────────────────────────── helpers ─────────────────────────────────────

    def _build_swatch(self, master, label_text: str, col: int):
        container = ctk.CTkFrame(master, fg_color="#1b1c24", corner_radius=10)
        container.grid(row=0, column=col, sticky="nsew", padx=5, pady=4)

        ctk.CTkLabel(
            container, text=label_text,
            font=("Segoe UI", 10), text_color="#7f88a3"
        ).pack(anchor="w", padx=10, pady=(8, 4))

        box = ctk.CTkFrame(container, fg_color="#232533", corner_radius=8, height=48)
        box.pack(fill="x", expand=False, padx=10, pady=(0, 10))
        box.pack_propagate(False)
        return box

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _open_config(self, path: str):
        if path and os.path.exists(path):
            content = BufferManager.read_file(path)
            if self.ctx.editor:
                self.ctx.editor.set_text(content)
            self.ctx.current_file = path
            self.ctx.is_dirty = False
            if self.ctx.status_bar:
                self.ctx.status_bar.update_status(1, 0, os.path.basename(path))
            self.destroy()

    def _get_theme_path(self, theme_name: str) -> Optional[str]:
        if ThemeManager:
            return ThemeManager.resolve_theme_path(theme_name)
        return None

    def _on_theme_selected(self, value: str):
        self.selected_theme = value
        self._render_theme_preview(value)

    def _render_theme_preview(self, theme_name: str):
        if ThemeManager:
            theme  = ThemeManager.load_theme(theme_name)
            editor = theme.get("editor", {})
            syntax = theme.get("syntax", {})
        else:
            editor, syntax = {}, {}

        self.bg_swatch.configure(fg_color=editor.get("bg", "#1e1e1e"))
        self.text_swatch.configure(fg_color=editor.get("fg", "#abb2bf"))
        self.accent_swatch.configure(fg_color=syntax.get("keyword", "#61afef"))
        self.preview_title.configure(
            text=f"Tema: {theme_name}",
            text_color="#ffffff",
        )

    def _apply_theme(self):
        if self.ctx.window:
            self.ctx.window.apply_theme(self.selected_theme)
            self._render_theme_preview(self.selected_theme)

    def _open_current_theme(self):
        self._open_config(self._get_theme_path(self.selected_theme))

    def _load_plugins(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = {
            "Core": os.path.join(base_dir, "core", "core_plugin"),
            "User": os.path.join(base_dir, "plugins"),
        }

        found = False
        for label, p in paths.items():
            if not os.path.exists(p):
                continue

            # Cabeçalho de seção
            section_color = "#61afef" if label == "Core" else "#98c379"
            section_frame = ctk.CTkFrame(
                self.scroll_plugins, fg_color="#1e1f28", corner_radius=10
            )
            section_frame.pack(fill="x", padx=8, pady=(10, 4))
            ctk.CTkLabel(
                section_frame,
                text=f"  {label}",
                font=("Segoe UI", 10, "bold"),
                text_color=section_color,
            ).pack(anchor="w", padx=12, pady=6)

            items = [
                i for i in sorted(os.listdir(p))
                if not i.startswith("__") and i != "init.py"
            ]

            if not items:
                ctk.CTkLabel(
                    self.scroll_plugins,
                    text="  Nenhum plugin nesta categoria",
                    font=("Segoe UI", 11), text_color="#3d3f52"
                ).pack(anchor="w", padx=20, pady=4)
                continue

            for item in items:
                found = True
                name = item.replace(".py", "")
                is_py = item.endswith(".py")

                row = ctk.CTkFrame(
                    self.scroll_plugins,
                    fg_color="#18181d",
                    corner_radius=8,
                    border_width=1,
                    border_color="#2b2b35",
                    height=44,
                )
                row.pack(fill="x", padx=8, pady=3)
                row.pack_propagate(False)

                # Dot de status
                dot = ctk.CTkFrame(row, fg_color=section_color, corner_radius=4, width=6, height=6)
                dot.pack(side="left", padx=(14, 0))

                ctk.CTkLabel(
                    row, text=name,
                    font=("Segoe UI", 12), text_color="#d3d5df"
                ).pack(side="left", padx=12)

                badge_text = ".py" if is_py else "pkg"
                ctk.CTkLabel(
                    row,
                    text=badge_text,
                    font=("Segoe UI", 9),
                    text_color="#3d3f52",
                ).pack(side="right", padx=14)

        if not found:
            ctk.CTkLabel(
                self.scroll_plugins,
                text="Nenhum plugin detectado.",
                font=("Segoe UI", 12),
                text_color="#3d3f52",
            ).pack(pady=30)