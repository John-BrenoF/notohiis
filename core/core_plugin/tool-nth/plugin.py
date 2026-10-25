import json
import os
import sys

from notohiis_core import (
    CONTENT_CHANGED,
    FILE_CHANGED,
    LINE_NUMBERS_REDRAWN,
    THEME_CHANGED,
)

DIRETORIO_TOOL = os.path.dirname(os.path.abspath(__file__))

if DIRETORIO_TOOL not in sys.path:
    sys.path.insert(0, DIRETORIO_TOOL)

import tool_nth
from pseUI.debug_bar import BarraDeDepuracao
from pseUI.gutter_markers import MarcadoresDoGutter

ATRASO_BOMBEIO_MS = 80
TAG_PARADA = "nth_debug_parada"
ROTULOS_MOTIVO = {
    "breakpoint": "breakpoint",
    "passo": "passo",
    "pausa": "pausa",
    "excecao": "exceção",
}

class Depurador:
    def __init__(self, ctx):
        self.ctx = ctx
        self.sessao = tool_nth.SessaoDeDepuracao()
        self.barra = None
        self.ativo = False
        self.bombeio_agendado = False
        self.quadro_selecionado = 0
        self.marcadores = MarcadoresDoGutter(ctx, self)
        self._vincular_atalhos()
        self._ouvir_eventos()

    def _acoes(self):
        return {
            "continuar": self.continuar_ou_iniciar,
            "pausar": self.pausar,
            "passo": self.passo_sobre,
            "dentro": self.passo_dentro,
            "fora": self.passo_fora,
            "parar": self.parar_sessao,
            "avaliar": self.avaliar,
            "selecionar_quadro": self.selecionar_quadro,
            "abrir_ponto": self.abrir_ponto,
            "remover_ponto": self.remover_ponto,
            "limpar_pontos": self.limpar_pontos,
        }

    def _vincular_atalhos(self):
        janela = getattr(self.ctx, "window", None)
        if janela is None:
            return
        janela.bind("<Control-Alt-d>", self.alternar_barra, add="+")
        janela.bind("<Control-Alt-D>", self.alternar_barra, add="+")
        janela.bind("<F5>", self.continuar_ou_iniciar, add="+")
        janela.bind("<F9>", self.alternar_ponto, add="+")
        janela.bind("<F10>", self.passo_sobre, add="+")
        janela.bind("<F11>", self.passo_dentro, add="+")
        janela.bind("<Shift-F11>", self.passo_fora, add="+")
        janela.bind("<Shift-F5>", self.parar_sessao, add="+")

    def _ouvir_eventos(self):
        eventos = getattr(self.ctx, "events", None)
        if eventos is None:
            return
        eventos.on(LINE_NUMBERS_REDRAWN, self._ao_redesenhar_gutter)
        eventos.on(FILE_CHANGED, self._ao_trocar_arquivo)
        eventos.on(CONTENT_CHANGED, self._ao_mudar_conteudo)
        eventos.on(THEME_CHANGED, self._ao_mudar_tema)

    def _ao_redesenhar_gutter(self, _evento=None):
        try:
            self.marcadores.desenhar()
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")

    def _ao_trocar_arquivo(self, _arquivo=None):
        try:
            self.marcadores.desenhar()
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")

    def _ao_mudar_conteudo(self, _conteudo=None):
        try:
            self.revalidar_pontos()
            self.marcadores.desenhar()
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")

    def _ao_mudar_tema(self, _tema=None):
        try:
            barra = self._garantir_barra()
            if barra is not None:
                barra.aplicar_tema(getattr(self.ctx, "theme", {}) or {})
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")

    def _garantir_barra(self):
        if self.barra is not None:
            return self.barra
        if getattr(self.ctx, "window", None) is None:
            return None
        try:
            self.barra = BarraDeDepuracao(self.ctx, self._acoes()).montar()
            self.barra.aplicar_tema(getattr(self.ctx, "theme", {}) or {})
        except Exception as erro:
            print(f"[TOOL-NTH] barra indisponível: {erro}")
            self.barra = None
        return self.barra

    def alternar_barra(self, _evento=None):
        try:
            barra = self._garantir_barra()
            if barra is not None:
                barra.alternar()
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
        return "break"

    def arquivo_util(self):
        atual = getattr(self.ctx, "current_file", None)
        if not atual or not str(atual).endswith(".py"):
            return None
        caminho = os.path.abspath(str(atual))
        if not os.path.isfile(caminho):
            return None
        return caminho

    def iniciar_sessao(self):
        arquivo = self.arquivo_util()
        if arquivo is None:
            self._abrir_barra()
            self._mensagem("[depuração] abra um arquivo .py para depurar\n")
            return
        if getattr(self.ctx, "is_dirty", False) and not self._salvar_atual():
            self._abrir_barra()
            self._mensagem("[depuração] não consegui salvar o arquivo\n")
            return
        barra = self._abrir_barra()
        if barra is not None:
            barra.limpar_paineis()
        try:
            iniciado = self.sessao.iniciar(
                arquivo, [], sys.executable, DIRETORIO_TOOL
            )
        except Exception as erro:
            self._mensagem(f"[depuração] falha ao iniciar: {erro}\n")
            return
        if not iniciado:
            self._mensagem("[depuração] a sessão não iniciou\n")
            return
        self.ativo = True
        self.quadro_selecionado = 0
        self._agendar_bombeio()
        self._mudar_estado("executando")
        self._status(f"Executando {os.path.basename(arquivo)}")
        self._mensagem(f"[depuração] iniciando {arquivo}\n")

    def continuar_ou_iniciar(self, _evento=None):
        try:
            estado = self.sessao.estado
            if estado == "parado":
                self.sessao.continuar()
                self._apos_retomada()
            elif estado in ("inativo", "encerrado"):
                self.iniciar_sessao()
        except Exception as erro:
            self._abrir_barra()
            self._mensagem(f"[depuração] erro: {erro}\n")
        return "break"

    def pausar(self, _evento=None):
        if self.sessao.estado == "executando":
            try:
                self.sessao.pausar()
            except Exception as erro:
                self._mensagem(f"[depuração] erro: {erro}\n")
        return "break"

    def parar_sessao(self, _evento=None):
        if self.sessao.estado in ("parado", "executando"):
            try:
                self.sessao.parar()
            except Exception as erro:
                print(f"[TOOL-NTH] {erro}")
            self._encerrar_sessao("interrompido")
            self._mensagem("[depuração] sessão interrompida\n")
        return "break"

    def passo_sobre(self, _evento=None):
        return self._passo("passo_sobre")

    def passo_dentro(self, _evento=None):
        return self._passo("passo_dentro")

    def passo_fora(self, _evento=None):
        return self._passo("passo_fora")

    def _passo(self, metodo):
        if self.sessao.estado != "parado":
            return "break"
        try:
            getattr(self.sessao, metodo)()
            self._apos_retomada()
        except Exception as erro:
            self._mensagem(f"[depuração] erro: {erro}\n")
        return "break"

    def _apos_retomada(self):
        self._limpar_marcador_de_parada()
        self._mudar_estado("executando")
        self._status("Executando…")

    def _encerrar_sessao(self, motivo):
        self.ativo = False
        self._limpar_marcador_de_parada()
        self._mudar_estado("inativo")
        self._status(f"Encerrado — {motivo}")
        barra = self._garantir_barra()
        if barra is not None:
            barra.pilha.limpar()
            barra.variaveis.limpar()

    def _limpar_marcador_de_parada(self):
        editor = getattr(self.ctx, "editor", None)
        if editor is None:
            return
        try:
            editor.delete_tag(TAG_PARADA)
        except Exception:
            pass

    def _agendar_bombeio(self):
        if self.bombeio_agendado:
            return
        janela = getattr(self.ctx, "window", None)
        if janela is None:
            return
        try:
            janela.after(ATRASO_BOMBEIO_MS, self._bombear)
            self.bombeio_agendado = True
        except Exception:
            self.ativo = False

    def _bombear(self):
        self.bombeio_agendado = False
        if not self.ativo:
            return
        try:
            for bruto in self.sessao.drenar_eventos():
                self._tratar_evento(json.loads(bruto))
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
        if self.ativo:
            self._agendar_bombeio()

    def _tratar_evento(self, evento):
        tipo = evento.get("type")
        if tipo == "parado":
            self._ao_parar(evento)
        elif tipo == "saida":
            self._mensagem(evento.get("texto", ""))
        elif tipo == "erro":
            self._mensagem(f"{evento.get('mensagem', '')}\n", "erro")
        elif tipo == "conectado":
            self._status("Conectado ao alvo")
        elif tipo == "continuado":
            self._status("Executando…")
        elif tipo == "saiu":
            codigo = int(evento.get("codigo", -1))
            self._encerrar_sessao(f"código {codigo}")
            self._mensagem(f"[depuração] encerrado (código {codigo})\n")

    def _ao_parar(self, evento):
        barra = self._abrir_barra()
        self._mudar_estado("parado")
        self.quadro_selecionado = 0
        quadros = evento.get("quadros") or []
        arquivo = evento.get("arquivo") or ""
        linha = int(evento.get("linha") or 0)
        if barra is not None:
            barra.pilha.definir_quadros(quadros)
            self._carregar_variaveis(0)
        if evento.get("detalhe"):
            self._mensagem(f"{str(evento['detalhe']).rstrip()}\n", "erro")
        self._ir_para(arquivo, linha)
        rotulo = ROTULOS_MOTIVO.get(evento.get("motivo"), evento.get("motivo", ""))
        nome = os.path.basename(arquivo) if arquivo else "?"
        self._status(f"Pausado · {nome}:{linha} · {rotulo}")

    def selecionar_quadro(self, indice):
        self.quadro_selecionado = int(indice)
        barra = self._garantir_barra()
        if barra is None:
            return
        quadros = barra.pilha.quadros
        if 0 <= indice < len(quadros):
            quadro = quadros[indice]
            self._ir_para(quadro.get("arquivo"), int(quadro.get("linha") or 0))
        self._carregar_variaveis(indice)

    def _carregar_variaveis(self, indice):
        barra = self._garantir_barra()
        if barra is None:
            return
        bruto = self.sessao.pedir_variaveis(indice)
        if not bruto:
            return
        dados = json.loads(bruto)
        barra.variaveis.definir_variaveis(
            dados.get("locais", []), dados.get("globais", [])
        )

    def avaliar(self, expressao):
        barra = self._garantir_barra()
        if barra is None:
            return
        if self.sessao.estado != "parado":
            barra.console.adicionar_avaliacao(
                expressao, None, "pause a execução para avaliar expressões"
            )
            return
        bruto = self.sessao.pedir_avaliacao(expressao, self.quadro_selecionado)
        if not bruto:
            barra.console.adicionar_avaliacao(expressao, None, "sem resposta do alvo")
            return
        dados = json.loads(bruto)
        barra.console.adicionar_avaliacao(
            expressao, dados.get("resultado", ""), dados.get("erro")
        )

    def _ir_para(self, arquivo, linha):
        if not arquivo or not linha:
            return
        editor = getattr(self.ctx, "editor", None)
        if editor is None:
            return
        atual = os.path.abspath(str(getattr(self.ctx, "current_file", "") or ""))
        if atual != os.path.abspath(arquivo):
            ponte = getattr(self.ctx, "tab_bridge", None)
            if ponte is None:
                return
            try:
                ponte.open_file(arquivo)
            except Exception as erro:
                print(f"[TOOL-NTH] {erro}")
                return
        indice = f"{linha}.0"
        try:
            editor.set_cursor(indice)
            editor.textbox.see(indice)
            editor.configure_tag(TAG_PARADA, background="#3a2f14")
            editor.apply_tag(TAG_PARADA, indice, f"{linha}.end")
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")

    def pontos_do_arquivo(self, arquivo):
        try:
            return [int(item) for item in self.sessao.pontos_do_arquivo(arquivo)]
        except Exception:
            return []

    def alternar_ponto(self, _evento=None):
        arquivo = self.arquivo_util()
        editor = getattr(self.ctx, "editor", None)
        if arquivo is None or editor is None:
            self._abrir_barra()
            self._mensagem("[depuração] selecione um arquivo .py para marcar breakpoints\n")
            return "break"
        try:
            linha = int(str(editor.get_cursor_index()).split(".")[0])
        except Exception:
            return "break"
        self._alternar_ponto_em(arquivo, linha)
        return "break"

    def alternar_ponto_na_linha(self, linha):
        arquivo = self.arquivo_util()
        if arquivo is None:
            return
        self._alternar_ponto_em(arquivo, int(linha))

    def _alternar_ponto_em(self, arquivo, linha):
        validas = set(tool_nth.linhas_executaveis(self._conteudo(arquivo)))
        if linha not in validas:
            self._mensagem(f"[depuração] a linha {linha} não aceita breakpoint\n")
            self.marcadores.desenhar()
            return
        try:
            self.sessao.alternar_ponto(arquivo, linha)
        except Exception as erro:
            self._mensagem(f"[depuração] {erro}\n")
            return
        self.marcadores.desenhar()
        self._atualizar_pontos()

    def remover_ponto(self, arquivo, linha):
        try:
            restantes = [
                item
                for item in self.pontos_do_arquivo(arquivo)
                if item != int(linha)
            ]
            self.sessao.definir_pontos(arquivo, restantes)
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
            return
        self.marcadores.desenhar()
        self._atualizar_pontos()

    def limpar_pontos(self):
        try:
            self.sessao.limpar_pontos()
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
            return
        self.marcadores.desenhar()
        self._atualizar_pontos()

    def abrir_ponto(self, arquivo, linha):
        self._ir_para(arquivo, int(linha))

    def revalidar_pontos(self):
        arquivo = self.arquivo_util()
        if arquivo is None:
            return
        atuais = set(self.pontos_do_arquivo(arquivo))
        if not atuais:
            return
        validas = set(tool_nth.linhas_executaveis(self._conteudo(arquivo)))
        restantes = sorted(atuais & validas)
        if restantes == sorted(atuais):
            return
        try:
            self.sessao.definir_pontos(arquivo, restantes)
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
            return
        self._atualizar_pontos()

    def _conteudo(self, arquivo):
        editor = getattr(self.ctx, "editor", None)
        atual = os.path.abspath(str(getattr(self.ctx, "current_file", "") or ""))
        if editor is not None and atual == arquivo:
            try:
                return editor.get_text()
            except Exception:
                pass
        try:
            with open(arquivo, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:
            return ""

    def _atualizar_pontos(self):
        barra = self._garantir_barra()
        if barra is None:
            return
        pontos = []
        try:
            for arquivo, linhas in self.sessao.todos_os_pontos():
                for linha in linhas:
                    pontos.append((arquivo, int(linha)))
        except Exception as erro:
            print(f"[TOOL-NTH] {erro}")
            return
        barra.pontos.definir_pontos(pontos)

    def _abrir_barra(self):
        barra = self._garantir_barra()
        if barra is not None:
            barra.mostrar()
        return barra

    def _mensagem(self, texto, estilo=None):
        barra = self._garantir_barra()
        if barra is not None:
            barra.console.adicionar_texto(texto, estilo)
        else:
            sys.stdout.write(texto)

    def _status(self, texto):
        barra = self._garantir_barra()
        if barra is not None:
            barra.definir_status(texto)

    def _mudar_estado(self, estado):
        barra = self._garantir_barra()
        if barra is not None:
            barra.mudar_estado(estado)

def setup(ctx):
    if getattr(ctx, "window", None) is None:
        print("[TOOL-NTH] janela indisponível — depurador não montado.")
        return None
    depurador = Depurador(ctx)
    try:
        ctx.external_plugins.append(depurador)
    except Exception as erro:
        print(f"[TOOL-NTH] registro incompleto: {erro}")
    print("[TOOL-NTH] depurador carregado — Ctrl+Alt+D abre a barra lateral")
    return depurador
