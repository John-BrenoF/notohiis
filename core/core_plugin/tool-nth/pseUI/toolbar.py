import tkinter.font as tkfont

import customtkinter as ctk

FAMILIAS_ICONES = (
    "JetBrainsMono Nerd Font Mono",
    "CaskaydiaCove Nerd Font Mono",
    "MesloLGL Nerd Font Mono",
    "MesloLGM Nerd Font Mono",
    "Hack Nerd Font Mono",
    "FiraCode Nerd Font Mono",
)

ICONES = {
    "iniciar": "",
    "continuar": "",
    "pausar": "",
    "passo": "",
    "dentro": "",
    "fora": "",
    "parar": "",
}

GLIFOS_TEXTO = {
    "iniciar": "▶",
    "continuar": "▶",
    "pausar": "⏸",
    "passo": "⏭",
    "dentro": "⬇",
    "fora": "⬆",
    "parar": "⏹",
}

def familia_de_icones():
    familias = tkfont.families()
    for nome in FAMILIAS_ICONES:
        if nome in familias:
            return nome
    for nome in familias:
        if "Nerd Font" in nome and "Mono" in nome:
            return nome
    return None

class BarraDeFerramentas(ctk.CTkFrame):
    def __init__(self, master, acoes):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.acoes = acoes
        self.botoes = {}
        self.familia = familia_de_icones()
        self.glifos = ICONES if self.familia else GLIFOS_TEXTO
        self.tamanho_icone = 18 if self.familia else 15
        itens = ("continuar", "pausar", "passo", "dentro", "fora", "parar")
        for indice, chave in enumerate(itens):
            botao = ctk.CTkButton(
                self,
                text=self.glifos[chave],
                width=46,
                height=32,
                corner_radius=6,
                font=self.fonte_icone(),
                command=self.acoes[chave],
            )
            botao.grid(row=0, column=indice, padx=(0, 6), pady=(2, 0))
            self.botoes[chave] = botao
        self.atalhos = ctk.CTkLabel(
            self,
            text="F5 continuar · F10 passo · F11 dentro · Shift+F11 saída · Shift+F5 parar · F9 breakpoint",
            anchor="w",
            justify="left",
            wraplength=320,
        )
        self.atalhos.grid(row=1, column=0, columnspan=len(itens), sticky="ew", pady=(8, 0))
        self.grid_columnconfigure(len(itens) - 1, weight=1)

    def fonte_icone(self):
        if not self.familia:
            return None
        return (self.familia, self.tamanho_icone)

    def definir_estado(self, estado):
        rodando = estado == "executando"
        parado = estado == "parado"
        self.botoes["continuar"].configure(
            state="disabled" if rodando else "normal",
            text=self.glifos["continuar"] if parado else self.glifos["iniciar"],
        )
        self.botoes["pausar"].configure(state="normal" if rodando else "disabled")
        for chave in ("passo", "dentro", "fora"):
            self.botoes[chave].configure(state="normal" if parado else "disabled")
        self.botoes["parar"].configure(state="normal" if (rodando or parado) else "disabled")

    def aplicar_tema(self, tema):
        editor = tema.get("editor", {})
        status = tema.get("status_bar", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        destaque = editor.get("gutter_fg", "#858585")
        for botao in self.botoes.values():
            botao.configure(
                fg_color=destaque,
                hover_color=texto,
                text_color="#101014",
                font=self.fonte_icone(),
            )
        self.atalhos.configure(text_color=texto, font=("Consolas", 10))
        self.configure(fg_color=fundo)
