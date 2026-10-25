import tkinter as tk

import customtkinter as ctk

class PainelConsole(ctk.CTkFrame):
    def __init__(self, master, ao_avaliar):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.ao_avaliar = ao_avaliar
        self.rotulo = ctk.CTkLabel(
            self, text="CONSOLE", anchor="w", font=("Consolas", 11, "bold")
        )
        self.rotulo.grid(row=0, column=0, sticky="ew")
        self.texto = tk.Text(
            self,
            height=6,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            state="disabled",
            font=("Consolas", 11),
            spacing1=1,
            spacing3=1,
        )
        self.texto.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.texto.tag_configure("erro", foreground="#e06c75")
        self.texto.tag_configure("entrada", foreground="#61afef")
        self.entrada = ctk.CTkEntry(
            self,
            placeholder_text="avaliar expressão (Enter)",
            height=28,
            font=("Consolas", 11),
        )
        self.entrada.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.entrada.bind("<Return>", self._enviar)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def adicionar_texto(self, texto, estilo=None):
        self.texto.configure(state="normal")
        if estilo:
            self.texto.insert(tk.END, texto, estilo)
        else:
            self.texto.insert(tk.END, texto)
        self.texto.see(tk.END)
        self.texto.configure(state="disabled")

    def adicionar_avaliacao(self, expressao, resultado, erro=None):
        self.adicionar_texto(f"> {expressao}\n", "entrada")
        if erro:
            self.adicionar_texto(f"{erro}\n", "erro")
        else:
            self.adicionar_texto(f"{resultado}\n")

    def limpar(self):
        self.texto.configure(state="normal")
        self.texto.delete("1.0", tk.END)
        self.texto.configure(state="disabled")

    def _enviar(self, _evento=None):
        expressao = self.entrada.get().strip()
        self.entrada.delete(0, tk.END)
        if not expressao:
            return "break"
        if self.ao_avaliar:
            self.ao_avaliar(expressao)
        return "break"

    def aplicar_tema(self, tema):
        editor = tema.get("editor", {})
        status = tema.get("status_bar", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        base = editor.get("bg", "#1e1e1e")
        self.rotulo.configure(text_color=texto)
        self.texto.configure(bg=base, fg=texto, insertbackground=texto)
        self.texto.tag_configure("erro", foreground="#e06c75")
        self.texto.tag_configure("entrada", foreground="#61afef")
        self.entrada.configure(
            fg_color=fundo,
            text_color=texto,
            border_color=editor.get("gutter_fg", "#858585"),
            placeholder_text_color=texto,
        )
