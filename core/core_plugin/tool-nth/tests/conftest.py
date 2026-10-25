import json
import os
import sys
import time

import pytest

DIRETORIO_TESTES = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_TOOL = os.path.abspath(os.path.join(DIRETORIO_TESTES, ".."))
RAIZ = os.path.abspath(os.path.join(DIRETORIO_TOOL, "..", "..", ".."))

for caminho in (DIRETORIO_TOOL, RAIZ):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

import tool_nth

class BombeiroDeEventos:
    def __init__(self, sessao, espera=8.0):
        self.sessao = sessao
        self.espera = espera
        self.eventos = []
        self.devolvidos = set()

    def iniciar(self, arquivo, pontos=(), argumentos=()):
        for linha in pontos:
            self.sessao.alternar_ponto(arquivo, int(linha))
        iniciado = self.sessao.iniciar(
            arquivo, list(argumentos), sys.executable, DIRETORIO_TOOL
        )
        assert iniciado, "a sessão não iniciou"
        self.esperar("conectado")
        return self

    def _achar(self, tipo, valido):
        for evento in self.eventos:
            if evento.get("type") != tipo:
                continue
            if valido is not None and not valido(evento):
                continue
            if id(evento) in self.devolvidos:
                continue
            self.devolvidos.add(id(evento))
            return evento
        return None

    def esperar(self, tipo, valido=None, espera=None):
        encontrado = self._achar(tipo, valido)
        if encontrado is not None:
            return encontrado
        limite = time.time() + (espera if espera is not None else self.espera)
        while time.time() < limite:
            for bruto in self.sessao.drenar_eventos():
                self.eventos.append(json.loads(bruto))
            encontrado = self._achar(tipo, valido)
            if encontrado is not None:
                return encontrado
            time.sleep(0.02)
        return None

    def parada(self, espera=None):
        return self.esperar(
            "parado", espera=espera
        )

    def houve(self, tipo):
        return any(evento.get("type") == tipo for evento in self.eventos)

    def texto_de_saida(self):
        return "".join(
            evento.get("texto", "")
            for evento in self.eventos
            if evento.get("type") == "saida"
        )

    def encerramento(self, espera=None):
        return self.esperar("saiu", espera=espera)

    def parar(self):
        try:
            if self.sessao.estado in ("executando", "parado"):
                self.sessao.parar()
        except Exception:
            pass

@pytest.fixture
def escrever_alvo(tmp_path):
    def criar(conteudo, nome="alvo.py"):
        destino = tmp_path / nome
        destino.write_text(conteudo, encoding="utf-8")
        return str(destino)

    return criar

@pytest.fixture
def sessao():
    instancia = tool_nth.SessaoDeDepuracao()
    yield instancia
    try:
        if instancia.estado in ("executando", "parado"):
            instancia.parar()
    except Exception:
        pass

@pytest.fixture
def bombeiro(sessao):
    instancia = BombeiroDeEventos(sessao)
    yield instancia
    instancia.parar()
