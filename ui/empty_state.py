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
from PIL import Image, ImageColor, ImageOps
from notohiis_core import AppContext

CAMINHO_ICONE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "midia", "icon", "icon.png")
)
ALTURA_ICONE = 128
LARGURA_DESCRICAO = 190

ATALHOS = (
    ("Ajuda", "F1"),
    ("Nova aba", "Ctrl+N"),
    ("Abrir pasta", "Ctrl+O"),
    ("Acesso rápido", "Ctrl+R"),
    ("Barra lateral", "Ctrl+B"),
    ("Painel de controle", "Ctrl+Alt+C"),
)


def misturar(origem: str, alvo: str, proporcao: float) -> str:
    r1, g1, b1 = ImageColor.getrgb(origem)
    r2, g2, b2 = ImageColor.getrgb(alvo)
    r = int(r1 + (r2 - r1) * proporcao)
    g = int(g1 + (g2 - g1) * proporcao)
    b = int(b1 + (b2 - b1) * proporcao)
    return f"#{r:02x}{g:02x}{b:02x}"


class EmptyStateView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self.ctx = AppContext()
        self._imagem_icone = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        conteudo = ctk.CTkFrame(self, fg_color="transparent")
        conteudo.grid(row=1, column=1)

        self.icone = ctk.CTkLabel(conteudo, text="")
        self.icone.grid(row=0, column=0, pady=(0, 12))

        self.titulo = ctk.CTkLabel(
            conteudo, text="bem vindo", font=("Segoe UI", 18, "bold")
        )
        self.titulo.grid(row=1, column=0, pady=(0, 10))

        atalhos = ctk.CTkFrame(conteudo, fg_color="transparent")
        atalhos.grid(row=2, column=0)
        atalhos.grid_columnconfigure(0, weight=1, minsize=LARGURA_DESCRICAO)
        atalhos.grid_columnconfigure(1, weight=0)

        self.rotulos = []
        self.caixas_de_teclas = []
        for indice, (descricao, teclas) in enumerate(ATALHOS):
            rotulo = ctk.CTkLabel(atalhos, text=descricao, anchor="w")
            rotulo.grid(row=indice, column=0, sticky="ew", pady=2)
            caixa = ctk.CTkFrame(atalhos, corner_radius=4, border_width=1)
            caixa.grid(row=indice, column=1, sticky="e", padx=(16, 0), pady=2)
            texto = ctk.CTkLabel(caixa, text=teclas, font=("Consolas", 11, "bold"))
            texto.pack(padx=8, pady=2)
            self.rotulos.append(rotulo)
            self.caixas_de_teclas.append((caixa, texto))

        self.apply_theme()

    def apply_theme(self):
        tema = self.ctx.theme.get("editor", {})
        fundo = tema.get("bg", "#141417")
        frente = tema.get("fg", "#d4d4d4")

        self.titulo.configure(text_color=misturar(fundo, frente, 0.92))
        for rotulo in self.rotulos:
            rotulo.configure(text_color=misturar(fundo, frente, 0.6))
        for caixa, texto in self.caixas_de_teclas:
            caixa.configure(
                fg_color=misturar(fundo, frente, 0.12),
                border_color=misturar(fundo, frente, 0.3),
            )
            texto.configure(text_color=misturar(fundo, frente, 0.85))
        self._redestinar_icone(fundo, frente)

    def _redestinar_icone(self, fundo: str, frente: str):
        try:
            original = Image.open(CAMINHO_ICONE).convert("RGBA")
        except FileNotFoundError:
            return
        mascara = original.getchannel("A")
        limites = mascara.getbbox()
        if limites is None:
            return
        recorte = original.crop(limites)
        tons = ImageOps.colorize(
            recorte.convert("L"),
            black=misturar(fundo, frente, 0.45),
            white=misturar(fundo, frente, 0.95),
        )
        tons.putalpha(mascara.crop(limites))
        largura = max(1, round(tons.width * ALTURA_ICONE / tons.height))
        redimensionada = tons.resize((largura, ALTURA_ICONE), Image.LANCZOS)
        self._imagem_icone = ctk.CTkImage(redimensionada, size=(largura, ALTURA_ICONE))
        self.icone.configure(image=self._imagem_icone)
