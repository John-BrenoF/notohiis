#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import os
import math
import datetime
import customtkinter as ctk
from PIL import Image, ImageFilter


def _saudacao() -> str:
    hora = datetime.datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia!"
    elif 12 <= hora < 18:
        return "Boa tarde!"
    else:
        return "Boa noite!"


def _ease_in_out(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _outline_png(image: Image.Image, color=(120, 122, 132, 255), thickness=4) -> Image.Image:

    image = image.convert("RGBA")
    alpha = image.split()[3]

    dilated_alpha = alpha.filter(ImageFilter.MaxFilter(thickness * 2 + 1))

    outline_layer = Image.new("RGBA", image.size, color)
    outline_layer.putalpha(dilated_alpha)

    return Image.alpha_composite(outline_layer, image)


class WelcomeWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Notohiis")
        self.geometry("480x260")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._center_window(self, 480, 260)

        self._anim_running = True
        self._setup_styles()
        self._setup_content()

        self._animate_dots()
        self._type_greeting()

    def _setup_styles(self):
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#000000")

    def _setup_content(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=24)

        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        welcome_image_path = os.path.join(BASE_DIR, "midia", "icon", "nth.png")

        try:
            image = Image.open(welcome_image_path)
            image = _outline_png(image)
            welcome_image = ctk.CTkImage(image, size=(160, 160))
        except FileNotFoundError:
            welcome_image = ctk.CTkImage(Image.new("RGBA", (160, 160), color=(0, 0, 0, 0)), size=(160, 160))

        self.image_label = ctk.CTkLabel(
            container, image=welcome_image, text="",
            width=160, height=160,
        )
        self.image_label.image = welcome_image
        self.image_label.grid(row=0, column=0, sticky="nsw", padx=(0, 25))

        right = ctk.CTkFrame(container, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", pady=8)
        right.rowconfigure((0, 1, 2, 3, 4), weight=0)
        right.rowconfigure(5, weight=1)

        self.full_greeting = _saudacao()
        self.current_greeting_len = 0
        self.saudacao_lbl = ctk.CTkLabel(
            right,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color="#dcffff",
            anchor="w",
        )
        self.saudacao_lbl.grid(row=0, column=0, sticky="w", pady=(0, 2))

        title_lbl = ctk.CTkLabel(
            right,
            text="Notohiis",
            font=("Segoe UI", 28, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        )
        title_lbl.grid(row=1, column=0, sticky="w", pady=(0, 4))

        sep = ctk.CTkFrame(right, width=40, height=3,
                           fg_color="#232323", corner_radius=2)
        sep.grid(row=2, column=0, sticky="w", pady=(0, 12))

        sub_lbl = ctk.CTkLabel(
            right,
            text="Editor leve para pessoas\nque querem algo simples",
            font=("Segoe UI", 12),
            text_color="#C6C6CE",
            justify="left",
            anchor="w",
        )
        sub_lbl.grid(row=3, column=0, sticky="w")

        ver_lbl = ctk.CTkLabel(
            right,
            text="v0.4alpha",
            font=("Segoe UI", 11),
            text_color="#8C8C96",
            anchor="w",
        )
        ver_lbl.grid(row=4, column=0, sticky="w", pady=(8, 0))

        self.dot_container = ctk.CTkFrame(right, width=76, height=20, fg_color="transparent")
        self.dot_container.grid(row=5, column=0, sticky="se")

        self._dot_dim = (0x2A, 0x2A, 0x30)
        self._dot_bright = (0x6E, 0x7B, 0xFF)

        self.dots = []
        for i in range(3):
            dot = ctk.CTkFrame(self.dot_container, width=10, height=10, corner_radius=5, fg_color="#2A2A30")
            dot.place(x=i * 22, y=5)
            self.dots.append(dot)

        self.anim_t = 0.0

    def _type_greeting(self):
        if not self._anim_running:
            return

        if self.current_greeting_len < len(self.full_greeting):
            self.current_greeting_len += 1
            self.saudacao_lbl.configure(text=self.full_greeting[:self.current_greeting_len])
            self.after(60, self._type_greeting)

    @staticmethod
    def _lerp_color(c1, c2, f):
        r = int(c1[0] + (c2[0] - c1[0]) * f)
        g = int(c1[1] + (c2[1] - c1[1]) * f)
        b = int(c1[2] + (c2[2] - c1[2]) * f)
        return f"#{r:02X}{g:02X}{b:02X}"

    def _animate_dots(self):
        if not self._anim_running:
            return

        SPEED = 0.025
        self.anim_t = (self.anim_t + SPEED) % 1.0

        for i, dot in enumerate(self.dots):
            phase = (self.anim_t + i / len(self.dots)) % 1.0
            brightness = _ease_in_out(math.sin(phase * math.pi))
            color = self._lerp_color(self._dot_dim, self._dot_bright, brightness)
            dot.configure(fg_color=color)

        self.after(16, self._animate_dots)

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