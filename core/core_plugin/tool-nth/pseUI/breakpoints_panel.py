import os
import tkinter as tk

import customtkinter as ctk

class PainelPontos(ctk.CTkFrame):
    def __init__(self, master, acoes):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.acoes = acoes
        self.pontos = []
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.grid_columnconfigure(1, weight=1)
        rotulo = ctk.CTkLabel(
            cabecalho, text="BREAKPOINTS", anchor="w", font=("Consolas", 11, "bold")
        )
        rotulo.grid(row=0, column=0, sticky="w")
        self.botao_remover = ctk.CTkButton(
            cabecalho,
            text="remover",
            width=72,
            height=22,
            corner_radius=6,
            command=self._remover_selecionado,
            font=("Consolas", 10),
        )
        self.botao_remover.grid(row=0, column=1, sticky="e")
        self.botao_limpar = ctk.CTkButton(
            cabecalho,
            text="limpar",
            width=64,
            height=22,
            corner_radius=6,
            command=self._limpar_tudo,
            font=("Consolas", 10),
        )
        self.botao_limpar.grid(row=0, column=2, sticky="e", padx=(6, 0))
        self.rotulo = rotulo
        self.lista = tk.Listbox(
            self,
            height=3,
            exportselection=False,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            selectborderwidth=0,
            font=("Consolas", 11),
        )
        self.lista.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.lista.bind("<Double-Button-1>", self._abrir_selecionado)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def definir_pontos(self, pontos):
        self.pontos = [(arquivo, int(linha)) for arquivo, linha in pontos]
        self.lista.delete(0, tk.END)
        for arquivo, linha in self.pontos:
            self.lista.insert(tk.END, f"{os.path.basename(arquivo)}:{linha}   {arquivo}")

    def _indice_selecionado(self):
        selecao = self.lista.curselection()
        if not selecao or selecao[0] >= len(self.pontos):
            return None
        return selecao[0]

    def _remover_selecionado(self):
        indice = self._indice_selecionado()
        if indice is None:
            return
        arquivo, linha = self.pontos[indice]
        self.acoes["remover_ponto"](arquivo, linha)

    def _limpar_tudo(self):
        self.acoes["limpar_pontos"]()

    def _abrir_selecionado(self, _evento=None):
        indice = self._indice_selecionado()
        if indice is None:
            return
        arquivo, linha = self.pontos[indice]
        self.acoes["abrir_ponto"](arquivo, linha)

    def aplicar_tema(self, tema):
        editor = tema.get("editor", {})
        status = tema.get("status_bar", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        base = editor.get("bg", "#1e1e1e")
        self.rotulo.configure(text_color=texto)
        for botao in (self.botao_remover, self.botao_limpar):
            botao.configure(
                fg_color=editor.get("gutter_fg", "#858585"),
                hover_color=texto,
                text_color="#101014",
            )
        self.lista.configure(
            bg=base,
            fg=texto,
            selectbackground=editor.get("gutter_fg", "#858585"),
            selectforeground="#101014",
            highlightbackground=fundo,
        )
