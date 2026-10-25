import os
import tkinter as tk

from notohiis_core import FILE_CHANGED, LINE_NUMBERS_REDRAWN

COR_MARCADOR = "#e51400"
BORDA_MARCADOR = "#1e1e1e"

class MarcadoresDoGutter:
    def __init__(self, ctx, desenhavel):
        self.ctx = ctx
        self.desenhavel = desenhavel
        self.marcadores = []
        self.canvas = None
        self._prender_clique()
        ctx.events.on(LINE_NUMBERS_REDRAWN, self.desenhar)
        ctx.events.on(FILE_CHANGED, self._ao_trocar_arquivo)

    def _prender_clique(self):
        if self.canvas is not None:
            return
        editor = getattr(self.ctx, "editor", None)
        if editor is None:
            return
        canvas = getattr(editor, "line_numbers", None)
        if canvas is None:
            return
        canvas.bind("<Button-1>", self.ao_clicar, add="+")
        self.canvas = canvas

    def _ao_trocar_arquivo(self, _arquivo=None):
        try:
            self.desenhar()
        except Exception:
            pass

    def ao_clicar(self, evento):
        editor = getattr(self.ctx, "editor", None)
        if editor is None:
            return None
        interno = editor.textbox._textbox
        try:
            deslocamento = int(evento.widget.winfo_pointery()) - int(interno.winfo_rooty())
            indice = interno.index(f"@0,{deslocamento}")
        except tk.TclError:
            return None
        linha = int(str(indice).split(".")[0])
        self.desenhavel.alternar_ponto_na_linha(linha)
        return "break"

    def desenhar(self, _evento=None):
        self._prender_clique()
        editor = getattr(self.ctx, "editor", None)
        if editor is None:
            return
        canvas = getattr(editor, "line_numbers", None)
        if canvas is None:
            return
        for item in self.marcadores:
            canvas.delete(item)
        self.marcadores = []
        arquivo = getattr(self.ctx, "current_file", None)
        if not arquivo or not os.path.isfile(arquivo):
            return
        pontos = set(self.desenhavel.pontos_do_arquivo(arquivo))
        if not pontos:
            return
        interno = editor.textbox._textbox
        for linha in sorted(pontos):
            try:
                dline = interno.dlineinfo(f"{linha}.0")
            except tk.TclError:
                continue
            if dline is None:
                continue
            centro = dline[1] + dline[2] / 2
            marcador = canvas.create_oval(
                6,
                centro - 4,
                14,
                centro + 4,
                fill=COR_MARCADOR,
                outline=BORDA_MARCADOR,
            )
            self.marcadores.append(marcador)
