#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

# janela de boas vindas antes de abrir o editor
# layout: imagem à esquerda | texto + animação à direita
import os
import math
import datetime
import customtkinter as ctk
from PIL import Image


def _saudacao() -> str:
    hora = datetime.datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia!"
    elif 12 <= hora < 18:
        return "Boa tarde!"
    else:
        return "Boa noite!"


class WelcomeWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Notohiis")
        self.geometry("480x260")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._center_window(self, 480, 260)

        # estado da animação
        self._dot_phase = 0.0
        self._dot_labels = []
        self._anim_running = True

        # Configurações de estilo
        self._setup_styles()

        # Conteúdo da janela
        self._setup_content()

        # inicia animação dos pontinhos
        self._animate_dots()

    def _setup_styles(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#0E0E16")

    def _setup_content(self):
        # ── container principal com duas colunas ────────────────────────────
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        container.columnconfigure(0, weight=0)   # coluna imagem — tamanho fixo
        container.columnconfigure(1, weight=1)   # coluna texto  — expande
        container.rowconfigure(0, weight=1)

        # ── coluna esquerda: imagem ──────────────────────────────────────────
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        welcome_image_path = os.path.join(BASE_DIR, "midia", "imgs", "nore.png")
        image = Image.open(welcome_image_path)
        welcome_image = ctk.CTkImage(image, size=(160, 160))
        self.image_label = ctk.CTkLabel(
            container, image=welcome_image, text="",
            width=160, height=160,
        )
        self.image_label.image = welcome_image
        self.image_label.grid(row=0, column=0, sticky="nsw", padx=(0, 18))

        # ── coluna direita: texto ────────────────────────────────────────────
        right = ctk.CTkFrame(container, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure((0, 1, 2, 3, 4), weight=0)
        right.rowconfigure(5, weight=1)   # empurra pontinhos para baixo

        # saudação (bom dia / boa tarde / boa noite)
        saudacao_lbl = ctk.CTkLabel(
            right,
            text=_saudacao(),
            font=("Segoe UI", 13),
            text_color="#6A6ABA",
            anchor="w",
        )
        saudacao_lbl.grid(row=0, column=0, sticky="w", pady=(4, 0))

        # título
        title_lbl = ctk.CTkLabel(
            right,
            text="Notohiis",
            font=("Segoe UI", 26, "bold"),
            text_color="#DDDDF5",
            anchor="w",
        )
        title_lbl.grid(row=1, column=0, sticky="w", pady=(2, 4))

        # linha decorativa
        sep = ctk.CTkFrame(right, width=140, height=2,
                           fg_color="#4A4AE8", corner_radius=2)
        sep.grid(row=2, column=0, sticky="w", pady=(0, 10))

        # subtexto
        sub_lbl = ctk.CTkLabel(
            right,
            text="Editor leve para\npessoas que querem algo simples",
            font=("Segoe UI", 11),
            text_color="#55557A",
            justify="left",
            anchor="w",
        )
        sub_lbl.grid(row=3, column=0, sticky="w")

        # versão
        ver_lbl = ctk.CTkLabel(
            right,
            text="v0.4alpha",
            font=("Segoe UI", 10),
            text_color="#33334A",
            anchor="w",
        )
        ver_lbl.grid(row=4, column=0, sticky="w", pady=(6, 0))

        # ── pontinhos animados (canto inferior direito) ──────────────────────
        dot_frame = ctk.CTkFrame(right, fg_color="transparent")
        dot_frame.grid(row=5, column=0, sticky="se")

        for i in range(3):
            lbl = ctk.CTkLabel(
                dot_frame,
                text="●",
                font=("Segoe UI", 10),
                text_color="#4A4AE8",
                width=16,
            )
            lbl.grid(row=0, column=i, padx=3)
            self._dot_labels.append(lbl)

    # ── animação: onda senoidal com fase deslocada 120° entre os pontos ──────
    def _animate_dots(self):
        if not self._anim_running:
            return

        SPEED  = 0.20
        MIN_SZ = 8
        MAX_SZ = 16

        for i, lbl in enumerate(self._dot_labels):
            angle = self._dot_phase + i * (2 * math.pi / 3)
            t     = (math.sin(angle) + 1) / 2

            size  = int(MIN_SZ + t * (MAX_SZ - MIN_SZ))
            rg    = int(60 + t * 80)
            blue  = int(180 + t * 75)
            hex_c = f"#{rg:02X}{rg:02X}{blue:02X}"

            lbl.configure(font=("Segoe UI", size), text_color=hex_c)

        self._dot_phase += SPEED
        self.after(50, self._animate_dots)

    def _center_window(self, window, width, height):
        screen_width  = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max(0, (screen_width  // 2) - (width  // 2))
        y = max(0, (screen_height // 2) - (height // 2))
        window.geometry(f"{width}x{height}+{x}+{y}")

    def run(self):
        def _close():
            self._anim_running = False
            self.destroy()

        self.after(3000, _close)
        self.mainloop()


if __name__ == "__main__":
    app = WelcomeWindow()
    app.run()