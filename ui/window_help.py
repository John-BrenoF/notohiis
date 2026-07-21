#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import os
import customtkinter as ctk
from PIL import Image
from core.src.app_context import AppContext


class HelpWindow:
    SHORTCUTS = [
        ("Ctrl+N",          "Novo Arquivo"),
        ("Ctrl+S",          "Salvar"),
        ("Ctrl+O",          "Abrir Pasta"),
        ("Ctrl+R",          "Projetos Recentes"),
        ("Ctrl+B",          "Alternar Sidebar"),
        ("Ctrl+M",          "Markdown Preview"),
        ("Ctrl+G",          "Git Quick Commit"),
        ("Ctrl+A",          "Selecionar Tudo"),
        ("ctrl+alt+c",      "Painel de Controle"),
        ("Alt+↑/↓ + Num",  "Navegação Rápida"),
        ("F1",              "Ajuda"),
    ]

    def __init__(self, master):
        self.master = master
        self._build_window()

    def _build_window(self):
        self.window = ctk.CTkToplevel(self.master)
        self.window.title("Ajuda - Notohiis")
        self.window.attributes("-topmost", True)
        self._center_window(self.window, 440, 480)

        # Cabeçalho
        header_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(24, 0))

        icon_path = os.path.join(os.path.dirname(__file__), "..", "midia", "icon", "help_nore.png")
        icon_path = os.path.normpath(icon_path)

        icon_image = None
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
            icon_image = ctk.CTkImage(image, size=(40, 40))

        ctk.CTkLabel(
            header_frame,
            text="",
            image=icon_image,
            width=40,
            height=40,
            fg_color="transparent",
            bg_color="transparent",
        ).pack(side="left", padx=(0, 10))

        title_block = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_block.pack(side="left")

        ctk.CTkLabel(
            title_block,
            text="Atalhos do Notohiis",
            font=("Segoe UI", 17, "bold"),
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block,
            text="Referência rápida de teclado",
            font=("Segoe UI", 11),
            text_color="gray",
            anchor="w",
        ).pack(anchor="w")

        # Divisor
        ctk.CTkFrame(self.window, height=1, fg_color="#3a3a3a").pack(
            fill="x", padx=28, pady=(16, 0)
        )

        # Cabeçalho da tabela 
        col_header = ctk.CTkFrame(self.window, fg_color="transparent")
        col_header.pack(fill="x", padx=28, pady=(10, 4))

        ctk.CTkLabel(
            col_header,
            text="ATALHO",
            font=("Segoe UI", 9, "bold"),
            text_color="gray",
            width=130,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            col_header,
            text="AÇÃO",
            font=("Segoe UI", 9, "bold"),
            text_color="gray",
            anchor="w",
        ).pack(side="left")

        # lista de atalhos 
        shortcuts_frame = ctk.CTkScrollableFrame(
            self.window,
            fg_color="transparent",
            scrollbar_button_color="#3a3a3a",
            scrollbar_button_hover_color="#61afef",
        )
        shortcuts_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        for i, (key, desc) in enumerate(self.SHORTCUTS):
            row_color = "#1e1e1e" if i % 2 == 0 else "transparent"

            row = ctk.CTkFrame(
                shortcuts_frame,
                fg_color=row_color,
                corner_radius=6,
            )
            row.pack(fill="x", pady=2, padx=4)

            # Badge da tecla
            badge = ctk.CTkFrame(row, fg_color="#2a2d3a", corner_radius=5)
            badge.pack(side="left", padx=(10, 12), pady=7)

            ctk.CTkLabel(
                badge,
                text=key,
                font=("Consolas", 11, "bold"),
                text_color="#61afef",
                width=116,
                anchor="center",
                padx=8,
                pady=3,
            ).pack()

            ctk.CTkLabel(
                row,
                text=desc,
                font=("Segoe UI", 12),
                anchor="w",
            ).pack(side="left", pady=7)

        # Divisor
        ctk.CTkFrame(self.window, height=1, fg_color="#3a3a3a").pack(
            fill="x", padx=28, pady=(8, 0)
        )

        # Rodapé
        footer = ctk.CTkFrame(self.window, fg_color="transparent")
        footer.pack(fill="x", padx=28, pady=(12, 20))

        ctk.CTkLabel(
            footer,
            text="Notohiis v0.4α",
            font=("Segoe UI", 10),
            text_color="#555",
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Entendido",
            command=self.window.destroy,
            width=110,
            height=34,
            corner_radius=8,
            font=("Segoe UI", 12, "bold"),
            fg_color="#61afef",
            hover_color="#4e9fd9",
            text_color="#111",
        ).pack(side="right")

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