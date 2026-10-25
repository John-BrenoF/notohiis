import tkinter as tk

import customtkinter as ctk

class PainelVariaveis(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.locais = []
        self.globais = []
        self.escopo = "locais"
        self.cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        self.cabecalho.grid(row=0, column=0, sticky="ew")
        self.cabecalho.grid_columnconfigure(1, weight=1)
        self.rotulo = ctk.CTkLabel(
            self.cabecalho,
            text="VARIÁVEIS",
            anchor="w",
            font=("Consolas", 11, "bold"),
        )
        self.rotulo.grid(row=0, column=0, sticky="w")
        self.seletor = ctk.CTkSegmentedButton(
            self.cabecalho,
            values=("locais", "globais"),
            command=self._trocar_escopo,
            height=24,
            font=("Consolas", 10),
        )
        self.seletor.set("locais")
        self.seletor.grid(row=0, column=1, sticky="e")
        self.lista = tk.Listbox(
            self,
            height=6,
            exportselection=False,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            selectborderwidth=0,
            font=("Consolas", 11),
        )
        self.lista.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def definir_variaveis(self, locais, globais):
        self.locais = list(locais)
        self.globais = list(globais)
        self._renderizar()

    def limpar(self):
        self.locais = []
        self.globais = []
        self._renderizar()

    def _trocar_escopo(self, valor):
        self.escopo = valor
        self._renderizar()

    def _renderizar(self):
        itens = self.locais if self.escopo == "locais" else self.globais
        self.lista.delete(0, tk.END)
        for item in itens:
            self.lista.insert(
                tk.END,
                f"{item.get('nome', '?')} = {item.get('valor', '?')}   ({item.get('tipo', '?')})",
            )

    def aplicar_tema(self, tema):
        editor = tema.get("editor", {})
        status = tema.get("status_bar", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        base = editor.get("bg", "#1e1e1e")
        self.rotulo.configure(text_color=texto)
        self.seletor.configure(
            fg_color=base,
            selected_color=editor.get("gutter_fg", "#858585"),
            selected_hover_color=texto,
            unselected_color=fundo,
            unselected_hover_color=base,
            text_color=texto,
        )
        self.lista.configure(
            bg=base,
            fg=texto,
            selectbackground=editor.get("gutter_fg", "#858585"),
            selectforeground="#101014",
            highlightbackground=fundo,
        )
