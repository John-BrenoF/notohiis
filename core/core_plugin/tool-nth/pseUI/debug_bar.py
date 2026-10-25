import customtkinter as ctk
from notohiis_core import SessionManager

from pseUI.breakpoints_panel import PainelPontos
from pseUI.console_panel import PainelConsole
from pseUI.stack_panel import PainelPilha
from pseUI.toolbar import BarraDeFerramentas
from pseUI.variables_panel import PainelVariaveis

COLUNA_LATERAL = 2
LARGURA_PADRAO = 360
LARGURA_MINIMA = 240
LARGURA_MAXIMA_FRACAO = 0.65

class BarraDeDepuracao:
    def __init__(self, ctx, acoes):
        self.ctx = ctx
        self.acoes = acoes
        self.quadro = None
        self.visivel = False
        self.largura = LARGURA_PADRAO
        self._largura_inicial = LARGURA_PADRAO
        self._posicao_inicial = 0
        guardada = SessionManager.get_ui_setting("debug_bar_width", LARGURA_PADRAO)
        try:
            self.largura = int(guardada)
        except (TypeError, ValueError):
            self.largura = LARGURA_PADRAO

    def montar(self):
        janela = self.ctx.window
        self.quadro = ctk.CTkFrame(janela, corner_radius=0, fg_color="#21252b")
        self.quadro.grid_columnconfigure(0, weight=0, minsize=6)
        self.quadro.grid_columnconfigure(1, weight=1)
        self.quadro.grid_rowconfigure(0, weight=1)

        self.alca = ctk.CTkFrame(self.quadro, width=6, corner_radius=0, cursor="sb_h_double_arrow")
        self.alca.grid(row=0, column=0, sticky="nsew")
        self.alca.bind("<Button-1>", self._iniciar_redimensionamento)
        self.alca.bind("<B1-Motion>", self._redimensionar)
        self.alca.bind("<ButtonRelease-1>", self._encerrar_redimensionamento)

        conteudo = ctk.CTkFrame(self.quadro, corner_radius=0, fg_color="transparent")
        conteudo.grid(row=0, column=1, sticky="nsew")
        self.conteudo = conteudo

        cabecalho = ctk.CTkFrame(conteudo, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        cabecalho.grid_columnconfigure(1, weight=1)
        titulo = ctk.CTkLabel(
            cabecalho, text="DEBUG", anchor="w", font=("Consolas", 13, "bold")
        )
        titulo.grid(row=0, column=0, sticky="w")
        fechar = ctk.CTkButton(
            cabecalho, text="×", width=28, height=24, corner_radius=6, command=self.ocultar
        )
        fechar.grid(row=0, column=2, sticky="e")
        self.titulo = titulo
        self.botao_fechar = fechar

        self.ferramentas = BarraDeFerramentas(conteudo, self.acoes)
        self.ferramentas.grid(row=1, column=0, sticky="ew", padx=12, pady=(10, 0))

        self.status = ctk.CTkLabel(
            conteudo, text="Pronto — F5 inicia a depuração", anchor="w", justify="left", wraplength=330
        )
        self.status.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 0))

        self.pilha = PainelPilha(conteudo, self.acoes["selecionar_quadro"])
        self.pilha.grid(row=3, column=0, sticky="nsew", padx=12, pady=(10, 0))

        self.variaveis = PainelVariaveis(conteudo)
        self.variaveis.grid(row=4, column=0, sticky="nsew", padx=12, pady=(10, 0))

        self.pontos = PainelPontos(conteudo, self.acoes)
        self.pontos.grid(row=5, column=0, sticky="nsew", padx=12, pady=(10, 0))

        self.console = PainelConsole(conteudo, self.acoes["avaliar"])
        self.console.grid(row=6, column=0, sticky="nsew", padx=12, pady=(10, 12))

        for linha, peso in ((3, 1), (4, 2), (5, 1), (6, 2)):
            conteudo.grid_rowconfigure(linha, weight=peso)
        conteudo.grid_columnconfigure(0, weight=1)
        self.ferramentas.definir_estado("inativo")
        return self

    def mostrar(self):
        if self.quadro is None:
            self.montar()
        if self.visivel:
            return
        largura = max(LARGURA_MINIMA, self.largura)
        self.ctx.window.grid_columnconfigure(COLUNA_LATERAL, minsize=largura, weight=0)
        self.quadro.grid(
            row=0, column=COLUNA_LATERAL, rowspan=12, sticky="nsew", padx=(1, 0)
        )
        self.visivel = True

    def ocultar(self):
        if not self.visivel or self.quadro is None:
            return
        self.quadro.grid_forget()
        self.ctx.window.grid_columnconfigure(COLUNA_LATERAL, minsize=0, weight=0)
        self.visivel = False
        self.guardar_largura()

    def alternar(self):
        if self.visivel:
            self.ocultar()
        else:
            self.mostrar()

    def mudar_estado(self, estado):
        if self.ferramentas:
            self.ferramentas.definir_estado(estado)

    def definir_status(self, texto):
        if self.status:
            self.status.configure(text=texto)

    def limpar_paineis(self):
        self.pilha.limpar()
        self.variaveis.limpar()
        self.console.limpar()

    def aplicar_tema(self, tema):
        if self.quadro is None:
            return
        status = tema.get("status_bar", {})
        editor = tema.get("editor", {})
        fundo = status.get("bg", "#21252b")
        texto = status.get("fg", "#9da5b4")
        alca = editor.get("gutter_bg", "#1e1e1e")
        self.quadro.configure(fg_color=fundo)
        self.alca.configure(fg_color=alca)
        self.titulo.configure(text_color=texto)
        self.botao_fechar.configure(
            fg_color=editor.get("gutter_fg", "#858585"), hover_color=texto, text_color="#101014"
        )
        self.status.configure(text_color=texto, font=("Consolas", 11))
        self.ferramentas.aplicar_tema(tema)
        self.pilha.aplicar_tema(tema)
        self.variaveis.aplicar_tema(tema)
        self.pontos.aplicar_tema(tema)
        self.console.aplicar_tema(tema)

    def _iniciar_redimensionamento(self, evento):
        self._largura_inicial = self.largura
        self._posicao_inicial = evento.x_root

    def _redimensionar(self, evento):
        janela = self.ctx.window
        disponivel = max(janela.winfo_width() * LARGURA_MAXIMA_FRACAO, LARGURA_MINIMA)
        nova = self._largura_inicial + (self._posicao_inicial - evento.x_root)
        nova = int(max(LARGURA_MINIMA, min(nova, disponivel)))
        self.largura = nova
        janela.grid_columnconfigure(COLUNA_LATERAL, minsize=nova, weight=0)

    def _encerrar_redimensionamento(self, _evento):
        self.guardar_largura()

    def guardar_largura(self):
        try:
            SessionManager.set_ui_setting("debug_bar_width", int(self.largura))
        except Exception:
            pass
