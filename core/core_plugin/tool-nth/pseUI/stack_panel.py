import os
import tkinter as tk

import customtkinter as ctk

class PainelPilha(ctk.CTkFrame):
    def __init__(self, master, ao_selecionar):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.ao_selecionar = ao_selecionar
        self.quadros = []
        self.rotulo = ctk.CTkLabel(
            self, text="PILHA DE CHAMADAS", anchor="w", font=("Consolas", 11, "bold")
        )
        self.rotulo.grid(row=0, column=0, sticky="ew")
        self.lista = tk.Listbox(
            self,
            height=4,
            exportselection=False,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            selectborderwidth=0,
            font=("Consolas", 11),
        )
        self.lista.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.lista.bind("<<ListboxSelect>>", self._ao_selecionar)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def definir_quadros(self, quadros):
        self.quadros = list(quadros)
        self.lista.delete(0, tk.END)
        for quadro in self.quadros:
            nome = quadro.get("nome", "?")
            arquivo = os.path.basename(quadro.get("arquivo", ""))
            self.lista.insert(tk.END, f"{nome}   {arquivo}:{quadro.get('linha', 0)}")
        if self.quadros:
            self.lista.selection_set(0)
            self.lista.activate(0)

    def limpar(self):
        self.quadros = []
        self.lista.delete(0, tk.END)

    def _ao_selecionar(self, _evento=None):
        selecao = self.lista.curselection()
        if not selecao:
            return
        indice = selecao[0]
        if indice < len(self.quadros) and self.ao_selecionar:
            self.ao_selecionar(indice)

    def aplicar_tema(self, tema):
        editor = tema.get("editor", {})
        status = tema.get("status_bar", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        base = editor.get("bg", "#1e1e1e")
        self.rotulo.configure(text_color=texto)
        self.lista.configure(
            bg=base,
            fg=texto,
            selectbackground=editor.get("gutter_fg", "#858585"),
            selectforeground="#101014",
            highlightbackground=fundo,
        )
