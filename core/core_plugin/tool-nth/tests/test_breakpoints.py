import tool_nth

CONTEUDO_MULTILINHA = '''texto = """
primeira
segunda
"""
terminado = True
print("ok", terminado)
'''

def test_linhas_em_branco_e_comentario_nao_contam():
    conteudo = "\n# comentário\n\n    \n\nx = 1\n"
    assert tool_nth.linhas_executaveis(conteudo) == [6]

def test_comentario_apos_codigo_continua_executavel():
    assert tool_nth.linhas_executaveis("x = 1  # ok\n# y = 2\n") == [1]

def test_hash_dentro_de_string_nao_fecha_a_linha():
    assert tool_nth.linhas_executaveis('url = "http://a#b" + "#c"\n') == [1]

def test_texto_triplo_interior_nao_conta():
    conteudo = 'doc = """\nlinha dentro\nno_meio = 1\n"""\nfim = 2\n'
    assert tool_nth.linhas_executaveis(conteudo) == [1, 5]

def test_string_que_abre_e_fecha_na_mesma_linha():
    conteudo = 'a = """x"""\nb = "y"\nc = f"{a} z"\n'
    assert tool_nth.linhas_executaveis(conteudo) == [1, 2, 3]

def test_continuacao_de_colchete_e_barra():
    assert tool_nth.linhas_executaveis("chamar(\n    1,\n    2,\n)\npronto = True\n") == [
        1,
        5,
    ]
    assert tool_nth.linhas_executaveis("total = 1 + \\\n    2\noutro = 3\n") == [1, 3]

def test_decorador_def_e_else_contam():
    conteudo = "@decorar\ndef f():\n    pass\nelse_ = 0\n"
    assert tool_nth.linhas_executaveis(conteudo) == [1, 2, 3, 4]

def test_comentario_em_branco_apos_bloco():
    conteudo = "if 1:\n    pass\n\n# fim\nresultado = 1\n"
    assert tool_nth.linhas_executaveis(conteudo) == [1, 2, 5]

def test_alternar_definir_e_limpar_pontos(sessao, escrever_alvo):
    alvo = escrever_alvo("x = 1\n\ny = 2\nz = 3\n")
    assert sessao.alternar_ponto(alvo, 3) is True
    assert sessao.alternar_ponto(alvo, 1) is True
    assert sessao.pontos_do_arquivo(alvo) == [1, 3]
    assert sessao.alternar_ponto(alvo, 3) is False
    assert sessao.pontos_do_arquivo(alvo) == [1]

    sessao.definir_pontos(alvo, [4, 4, 2])
    assert sessao.pontos_do_arquivo(alvo) == [2, 4]
    assert dict(sessao.todos_os_pontos()) == {alvo: [2, 4]}

    outro = escrever_alvo("a = 1\n", nome="outro.py")
    sessao.alternar_ponto(outro, 1)
    assert len(sessao.todos_os_pontos()) == 2

    sessao.limpar_pontos()
    assert sessao.todos_os_pontos() == []
    assert sessao.pontos_do_arquivo(alvo) == []

def test_ponto_em_linha_de_texto_multilinha_nao_para(bombeiro, escrever_alvo):
    destino = escrever_alvo(CONTEUDO_MULTILINHA)
    bombeiro.iniciar(destino, pontos=(2, 3))
    encerrado = bombeiro.encerramento()
    assert encerrado["codigo"] == 0
    assert not bombeiro.houve("parado")
    assert "ok True" in bombeiro.texto_de_saida()

def test_ponto_em_comentario_nao_para(bombeiro, escrever_alvo):
    destino = escrever_alvo('# nada aqui\nprint("rodou")\n')
    bombeiro.iniciar(destino, pontos=(1,))
    encerrado = bombeiro.encerramento()
    assert encerrado["codigo"] == 0
    assert not bombeiro.houve("parado")

def test_remover_ponto_durante_a_execucao(bombeiro, escrever_alvo):
    destino = escrever_alvo('print("um")\nprint("dois")\nprint("tres")\n')
    bombeiro.iniciar(destino, pontos=(1,))
    parada = bombeiro.parada()
    assert parada is not None and parada["linha"] == 1

    bombeiro.sessao.definir_pontos(destino, [])
    assert bombeiro.sessao.pontos_do_arquivo(destino) == []
    bombeiro.sessao.continuar()
    encerrado = bombeiro.encerramento()
    assert encerrado["codigo"] == 0
    saida = bombeiro.texto_de_saida()
    assert "dois" in saida and "tres" in saida

def test_ponto_em_linha_de_continuacao_nao_para(bombeiro, escrever_alvo):
    destino = escrever_alvo("total = 1 + \\\n    2\nprint(total)\n")
    bombeiro.iniciar(destino, pontos=(2,))
    encerrado = bombeiro.encerramento()
    assert encerrado["codigo"] == 0
    assert not bombeiro.houve("parado")
