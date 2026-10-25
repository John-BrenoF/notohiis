import json
import time

CONTEUDO_EXCECAO = '''def quebrar():
    valor = 1
    raise ValueError("algo deu errado")


quebrar()
print("não deveria chegar aqui")
'''

CONTEUDO_PAUSA = '''import time

total = 0
for indice in range(200):
    total += indice
    if indice == 0:
        print("rodando")
    time.sleep(0.05)

print("terminou", total)
'''

def test_excecao_nao_tratada_para_com_rastro(escrever_alvo, bombeiro):
    destino = escrever_alvo(CONTEUDO_EXCECAO)
    bombeiro.iniciar(destino)
    parada = bombeiro.parada()
    assert parada is not None, "a exceção não parou a execução"
    assert parada["motivo"] == "excecao"
    assert parada["arquivo"] == destino
    assert parada["linha"] == 3
    assert "ValueError" in parada["detalhe"]
    assert "quebrar" in parada["detalhe"]
    assert destino in parada["detalhe"]
    assert [quadro["nome"] for quadro in parada["quadros"]] == ["quebrar", "<module>"]
    assert bombeiro.sessao.estado == "parado"

    bombeiro.sessao.continuar()
    encerrado = bombeiro.encerramento()
    assert encerrado is not None
    assert encerrado["codigo"] == 1
    assert "deveria chegar" not in bombeiro.texto_de_saida()

def test_excecao_com_pilha_de_varias_funcoes(escrever_alvo, bombeiro):
    destino = escrever_alvo(
        'def externa():\n    return interna()\n\n\ndef interna():\n'
        '    raise RuntimeError("fundo")\n\n\nexterna()\n'
    )
    bombeiro.iniciar(destino)
    parada = bombeiro.parada()
    assert parada is not None
    assert parada["motivo"] == "excecao"
    nomes = [quadro["nome"] for quadro in parada["quadros"]]
    assert nomes == ["interna", "externa", "<module>"]
    assert "RuntimeError: fundo" in parada["detalhe"]

def test_pausar_interrompe_a_executacao_em_movimento(escrever_alvo, bombeiro):
    destino = escrever_alvo(CONTEUDO_PAUSA)
    bombeiro.iniciar(destino)
    rodando = bombeiro.esperar(
        "saida", valido=lambda evento: "rodando" in evento.get("texto", "")
    )
    assert rodando is not None, "o alvo não chegou ao laço"

    bombeiro.sessao.pausar()
    parada = bombeiro.parada(espera=6.0)
    assert parada is not None, "pausar não interrompeu a execução"
    assert parada["motivo"] == "pausa"
    assert parada["arquivo"] == destino
    assert 4 <= parada["linha"] <= 8
    assert bombeiro.sessao.estado == "parado"

    variaveis = json.loads(bombeiro.sessao.pedir_variaveis(0))
    nomes = [item["nome"] for item in variaveis["locais"]]
    assert "total" in nomes
    assert "indice" in nomes

    bombeiro.sessao.continuar()
    retomado = bombeiro.esperar("continuado")
    assert retomado is not None
    bombeiro.sessao.parar()

def test_parar_encerra_o_alvo(escrever_alvo, bombeiro):
    destino = escrever_alvo(
        "import time\n\nfor indice in range(400):\n    time.sleep(0.05)\n"
    )
    bombeiro.iniciar(destino)
    bombeiro.sessao.parar()
    assert bombeiro.sessao.estado == "encerrado"
    time.sleep(0.3)
    assert not bombeiro.houve("parado")

def test_alvo_sem_breakpoints_executa_completo(escrever_alvo, bombeiro):
    destino = escrever_alvo('print("linha um")\nprint("linha dois")\n')
    bombeiro.iniciar(destino)
    encerrado = bombeiro.encerramento()
    assert encerrado["codigo"] == 0
    assert not bombeiro.houve("parado")
    saida = bombeiro.texto_de_saida()
    assert "linha um" in saida
    assert "linha dois" in saida
