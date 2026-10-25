import json

import pytest

CONTEUDO = '''def calcular(base):
    total = base * 2
    total = total + 1
    return total


resultado = calcular(21)
print("resultado", resultado)
print("fim")
'''

@pytest.fixture
def alvo(escrever_alvo):
    return escrever_alvo(CONTEUDO)

def test_pausa_no_breakpoint_e_expor_valores(bombeiro, alvo):
    bombeiro.iniciar(alvo, pontos=(8,))
    parada = bombeiro.parada()
    assert parada is not None, "não parou no breakpoint"
    assert parada["motivo"] == "breakpoint"
    assert parada["arquivo"] == alvo
    assert parada["linha"] == 8
    assert parada["quadros"][0]["nome"] == "<module>"

    variaveis = json.loads(bombeiro.sessao.pedir_variaveis(0))
    nomes = [item["nome"] for item in variaveis["locais"]]
    assert "resultado" in nomes
    assert any(item["valor"] == "43" for item in variaveis["locais"])

    avaliacao = json.loads(bombeiro.sessao.pedir_avaliacao("resultado + 1"))
    assert avaliacao["resultado"] == "44"
    assert avaliacao.get("erro") in (None, "")

def test_avaliacao_com_erro_retorna_mensagem(bombeiro, alvo):
    bombeiro.iniciar(alvo, pontos=(8,))
    bombeiro.parada()
    avaliacao = json.loads(bombeiro.sessao.pedir_avaliacao("nome_inexistente"))
    assert avaliacao.get("resultado") in (None, "")
    assert avaliacao.get("erro")

def test_passo_sobre_avanca_e_retoma(bombeiro, alvo):
    bombeiro.iniciar(alvo, pontos=(8,))
    bombeiro.parada()

    bombeiro.sessao.passo_sobre()
    seguinte = bombeiro.parada()
    assert seguinte is not None, "passo por cima não parou"
    assert seguinte["motivo"] == "passo"
    assert seguinte["linha"] == 9
    assert bombeiro.sessao.estado == "parado"

    bombeiro.sessao.continuar()
    retomado = bombeiro.esperar("continuado")
    assert retomado is not None

    encerrado = bombeiro.encerramento()
    assert encerrado is not None, "não encerrou"
    assert encerrado["codigo"] == 0
    saida = bombeiro.texto_de_saida()
    assert "resultado 43" in saida
    assert "fim" in saida

def test_passo_dentro_entra_na_funcao_e_passo_fora_volta(bombeiro, alvo):
    bombeiro.iniciar(alvo, pontos=(7,))
    primeira = bombeiro.parada()
    assert primeira["linha"] == 7

    bombeiro.sessao.passo_dentro()
    dentro = bombeiro.parada()
    assert dentro["motivo"] == "passo"
    assert dentro["linha"] == 2
    assert [quadro["nome"] for quadro in dentro["quadros"]] == ["calcular", "<module>"]

    variaveis = json.loads(bombeiro.sessao.pedir_variaveis(0))
    nomes = [item["nome"] for item in variaveis["locais"]]
    assert "base" in nomes

    bombeiro.sessao.passo_fora()
    fora = bombeiro.parada()
    assert fora["motivo"] == "passo"
    assert fora["linha"] == 8
    assert [quadro["nome"] for quadro in fora["quadros"]] == ["<module>"]

def test_pilha_com_dois_quadros_e_selecao(bombeiro, alvo):
    bombeiro.iniciar(alvo, pontos=(3,))
    parada = bombeiro.parada()
    assert parada["linha"] == 3
    assert len(parada["quadros"]) == 2

    quadros = parada["quadros"]
    assert quadros[0]["nome"] == "calcular"
    assert quadros[0]["linha"] == 3
    assert quadros[1]["nome"] == "<module>"
    assert quadros[1]["arquivo"] == alvo

    variaveis = json.loads(bombeiro.sessao.pedir_variaveis(0))
    assert any(item["nome"] == "total" for item in variaveis["locais"])

    reavaliado = json.loads(bombeiro.sessao.pedir_avaliacao("base * 3", 0))
    assert reavaliado["resultado"] == "63"

def test_saida_e_erro_do_alvo_sao_repassados(escrever_alvo, bombeiro):
    destino = escrever_alvo(
        'import sys\nprint("no stdout")\nsys.stderr.write("no stderr\\n")\nsys.exit(3)\n'
    )
    bombeiro.iniciar(destino)
    encerrado = bombeiro.encerramento()
    assert encerrado is not None
    assert encerrado["codigo"] == 3
    assert "no stdout" in bombeiro.texto_de_saida()

def test_pilha_filtra_quadros_de_biblioteca(escrever_alvo, bombeiro):
    destino = escrever_alvo(
        "import json\n\n\ndef ao_ler(dados):\n    copia = dict(dados)\n"
        "    print(copia)\n    return copia\n\n\n"
        "json.loads('{\"a\": 1}', object_hook=ao_ler)\n"
    )
    bombeiro.iniciar(destino, pontos=(6,))
    parada = bombeiro.parada()
    assert parada is not None, "não parou dentro da função"
    assert [quadro["nome"] for quadro in parada["quadros"]] == ["ao_ler", "<module>"]
    assert all("json" not in quadro["arquivo"] for quadro in parada["quadros"])

def test_estados_iniciais(sessao):
    assert sessao.estado == "inativo"
    assert sessao.porta > 0
    assert sessao.todos_os_pontos() == []
