import os
import json
import customtkinter as ctk
from PIL import Image
from core.src.app_context import AppContext

class HelpWindow:
    SHORTCUTS = [
        ("Ctrl+N", "Novo Arquivo"),
        ("Ctrl+S", "Salvar"),
        ("Ctrl+O", "Abrir Pasta"),
        ("Ctrl+R", "Projetos Recentes"),
        ("Ctrl+B", "Alternar Sidebar"),
        ("Ctrl+M", "Markdown Preview"),
        ("Ctrl+G", "Git Quick Commit"),
        ("Ctrl+A", "Selecionar Tudo"),
        ("ctrl+alt+c", "Painel de Controle"),
        ("Alt+↑/↓ + Num", "Navegação Rápida"),
        ("F1", "Ajuda"),
    ]

    def __init__(self, master):
        self.master = master
        self._load_theme()
        self._build_window()

    def _load_theme(self):
        self.colors = {
            "bg": "#1e2127", "panel": "#282c34", "panel_alt": "#21252b",
            "border": "#3a3f4b", "text": "#cccccc", "text_dim": "#7f848e",
            "accent": "#61afef", "accent_hover": "#4d94d6"
        }
        try:
            base_dir = os.getcwd()
            pref_path = os.path.join(base_dir, "ui", "preferencias", "preferecia.json")
            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                theme_name = prefs.get("selected_theme")
                if theme_name:
                    theme_path = os.path.join(base_dir, "ui", "estilo", f"{theme_name}.json")
                    if os.path.exists(theme_path):
                        with open(theme_path, "r", encoding="utf-8") as t:
                            theme = json.load(t)
                            editor = theme.get("editor", {})
                            sidebar = theme.get("sidebar", {})
                            status_bar = theme.get("status_bar", {})
                            syntax = theme.get("syntax", {})

                            self.colors["bg"] = editor.get("bg", self.colors["bg"])
                            self.colors["panel"] = status_bar.get("bg", self.colors["panel"])
                            self.colors["panel_alt"] = sidebar.get("bg", self.colors["panel_alt"])
                            self.colors["border"] = sidebar.get("label", self.colors["border"])
                            self.colors["text"] = editor.get("fg", self.colors["text"])
                            self.colors["text_dim"] = sidebar.get("fg", self.colors["text_dim"])
                            self.colors["accent"] = syntax.get("builtin", self.colors["accent"])
                            self.colors["accent_hover"] = syntax.get("keyword", self.colors["accent_hover"])
        except Exception:
            pass

    def _build_window(self):
        self.window = ctk.CTkToplevel(self.master)
        self.window.title("Ajuda - Notohiis")
        self.window.attributes("-topmost", True)
        self.window.configure(fg_color=self.colors["bg"])
        self._center_window(self.window, 460, 520)

        header_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(24, 16))

        base_dir = os.path.dirname(__file__)
        icon_path = os.path.normpath(os.path.join(base_dir, "..", "midia", "icon", "help_nore.png"))
        
        if os.path.exists(icon_path):
            img = ctk.CTkImage(Image.open(icon_path), size=(40, 40))
            ctk.CTkLabel(header_frame, text="", image=img, width=40, height=40).pack(side="left", padx=(0, 10))

        title_block = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_block.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(title_block, text="Atalhos do Notohiis", font=("Segoe UI", 17, "bold"), text_color=self.colors["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_block, text="Referência rápida de teclado", font=("Segoe UI", 11), text_color=self.colors["text_dim"], anchor="w").pack(anchor="w")

        col_header = ctk.CTkFrame(self.window, fg_color="transparent")
        col_header.pack(fill="x", padx=28, pady=(0, 4))
        
        ctk.CTkLabel(col_header, text="ATALHO", font=("Segoe UI", 9, "bold"), text_color=self.colors["text_dim"], width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(col_header, text="AÇÃO", font=("Segoe UI", 9, "bold"), text_color=self.colors["text_dim"], anchor="w").pack(side="left")

        ctk.CTkFrame(self.window, height=1, fg_color=self.colors["border"]).pack(fill="x", padx=28, pady=(0, 4))

        scroll = ctk.CTkScrollableFrame(self.window, fg_color="transparent", scrollbar_button_color=self.colors["border"], scrollbar_button_hover_color=self.colors["accent"])
        scroll.pack(fill="both", expand=True, padx=20, pady=0)

        for key, desc in self.SHORTCUTS:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=0, padx=4)
            
            content = ctk.CTkFrame(row, fg_color="transparent")
            content.pack(fill="x", pady=(8, 8))
            
            ctk.CTkLabel(content, text=key, font=("Consolas", 11, "bold"), text_color=self.colors["accent"], width=130, anchor="w").pack(side="left", padx=(8, 12))
            ctk.CTkLabel(content, text=desc, font=("Segoe UI", 12), text_color=self.colors["text"], anchor="w").pack(side="left")

            ctk.CTkFrame(row, height=1, fg_color=self.colors["border"]).pack(fill="x")

        footer = ctk.CTkFrame(self.window, fg_color="transparent")
        footer.pack(fill="x", padx=28, pady=(12, 20))
        
        ctk.CTkLabel(footer, text="Notohiis v0.4α", font=("Segoe UI", 10), text_color=self.colors["text_dim"], anchor="w").pack(side="left")
        
        ctk.CTkButton(
            footer, text="Entendido", command=self.window.destroy, 
            width=110, height=34, corner_radius=0, border_width=1, 
            border_color=self.colors["border"], font=("Segoe UI", 12, "bold"), 
            fg_color="transparent", hover_color=self.colors["panel_alt"], text_color=self.colors["text"]
        ).pack(side="right")

    def _center_window(self, window, width, height):
        window.update_idletasks()
        master = AppContext().window
        if master:
            window.transient(master)
        window.resizable(False, False)
        sw = window.winfo_screenwidth()
        sh = window.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")