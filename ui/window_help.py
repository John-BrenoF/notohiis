import customtkinter as ctk
from core.src.app_context import AppContext

class HelpWindow:

    SHORTCUTS = [
        ("Ctrl+N", "Novo Arquivo"),
        ("Ctrl+S", "Salvar"),
        ("Ctrl+O", "Abrir Pasta"),
        ("Ctrl+B", "Alternar Sidebar"),
        ("Ctrl+M", "Markdown Preview"),
        ("Ctrl+G", "Git Quick Commit"),
        ("Ctrl+A", "Selecionar Tudo"),
        ("Alt+↑/↓ + Num", "Navegação Rápida"),
        ("F1", "Ajuda"),
    ]

    def __init__(self, master):
        self.master = master
        self._build_window()

    def _build_window(self):
        self.window = ctk.CTkToplevel(self.master)
        self.window.title("Ajuda - Notohiis")
        self.window.attributes("-topmost", True)
        self._center_window(self.window, 400, 350)

        ctk.CTkLabel(
            self.window,
            text="Atalhos do Notohiis",
            font=("Segoe UI", 18, "bold"),
            pady=20,
        ).pack()

        shortcuts_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        shortcuts_frame.pack(fill="both", expand=True, padx=40)

        for key, desc in self.SHORTCUTS:
            row = ctk.CTkFrame(shortcuts_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=key,
                font=("Consolas", 12, "bold"),
                text_color="#61afef",
                width=100,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Segoe UI", 12), anchor="w").pack(side="left")

        ctk.CTkButton(self.window, text="Entendido", command=self.window.destroy).pack(pady=20)

    def _center_window(self, window, width, height):
        window.update_idletasks()
        master = AppContext().window
        if master:
            window.transient(master)
        window.resizable(False, False)

        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max(0, (screen_width // 2) - (width // 2))
        y = max(0, (screen_height // 2) - (height // 2))
        window.geometry(f"{width}x{height}+{x}+{y}")
