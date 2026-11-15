import importlib.machinery
import importlib.util
import os

PREFIXO_BLOCO = "NTH-"
ARQUIVO_BLOCO_PYTHON = "plugin.py"
ARQUIVO_BLOCO_RUST = "Cargo.toml"
PASTA_RELEASE_RUST = os.path.join("target", "release")


def _subpastas_de_bloco(pasta_plugins):
    if not os.path.isdir(pasta_plugins):
        return []
    return sorted(
        nome
        for nome in os.listdir(pasta_plugins)
        if nome.startswith(PREFIXO_BLOCO)
        and os.path.isdir(os.path.join(pasta_plugins, nome))
    )


def _biblioteca_rust_compilada(caminho_bloco):
    for diretorio in (caminho_bloco, os.path.join(caminho_bloco, PASTA_RELEASE_RUST)):
        if not os.path.isdir(diretorio):
            continue
        candidatos = sorted(
            (nome for nome in os.listdir(diretorio) if nome.endswith(".so")),
            key=lambda nome: not nome.endswith(".abi3.so"),
        )
        for nome in candidatos:
            caminho = os.path.join(diretorio, nome)
            if os.path.isfile(caminho):
                return caminho
    raise FileNotFoundError(
        "extensão Rust não compilada — rode cargo build --release na pasta do bloco"
    )


def _entrada_do_bloco(caminho_bloco):
    caminho_python = os.path.join(caminho_bloco, ARQUIVO_BLOCO_PYTHON)
    if os.path.isfile(caminho_python):
        return caminho_python
    if os.path.isfile(os.path.join(caminho_bloco, ARQUIVO_BLOCO_RUST)):
        return _biblioteca_rust_compilada(caminho_bloco)
    raise ValueError(
        f"estrutura não reconhecida: {ARQUIVO_BLOCO_PYTHON} ou {ARQUIVO_BLOCO_RUST} ausente"
    )


def _nome_do_modulo_extensao(caminho):
    nome = os.path.basename(caminho)
    for sufixo in sorted(importlib.machinery.EXTENSION_SUFFIXES, key=len, reverse=True):
        if nome.endswith(sufixo):
            nome = nome[: -len(sufixo)]
            break
    if nome.startswith("lib"):
        nome = nome[3:]
    return nome


def _carrega_modulo(caminho_arquivo, nome_modulo):
    especimo = importlib.util.spec_from_file_location(nome_modulo, caminho_arquivo)
    if especimo is None or especimo.loader is None:
        raise ImportError(f"sem carregador para {os.path.basename(caminho_arquivo)}")
    modulo = importlib.util.module_from_spec(especimo)
    especimo.loader.exec_module(modulo)
    return modulo


def _setup_do_bloco(modulo):
    setup = getattr(modulo, "setup", None)
    if not callable(setup):
        raise AttributeError("bloco sem função setup(ctx)")
    return setup


def load_block_plugins(ctx, pasta_plugins=None):
    if pasta_plugins is None:
        pasta_plugins = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "plugins"
        )
    for nome_bloco in _subpastas_de_bloco(pasta_plugins):
        caminho_bloco = os.path.join(pasta_plugins, nome_bloco)
        try:
            caminho_entrada = _entrada_do_bloco(caminho_bloco)
            if caminho_entrada.endswith(".py"):
                nome_modulo = "bloco_" + "".join(
                    caractere if caractere.isalnum() else "_" for caractere in nome_bloco
                )
            else:
                nome_modulo = _nome_do_modulo_extensao(caminho_entrada)
            modulo = _carrega_modulo(caminho_entrada, nome_modulo)
            setup = _setup_do_bloco(modulo)
            setup(ctx)
        except Exception as erro:
            print(f"[BLOCO] Falha ao carregar {nome_bloco}: {erro}")
