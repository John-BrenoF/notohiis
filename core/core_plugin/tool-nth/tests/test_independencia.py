import importlib.util
import os

from notohiis_core import AppContext

DIRETORIO_TESTES = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_TOOL = os.path.abspath(os.path.join(DIRETORIO_TESTES, ".."))
RAIZ = os.path.abspath(os.path.join(DIRETORIO_TOOL, "..", "..", ".."))
SHIM = os.path.join(RAIZ, "plugins", "tool_nth.py")

PASTAS_IGNORADAS = {
    ".git",
    ".venv",
    "target",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "dist",
    "build",
}
EXTENSOES = (".py", ".rs", ".toml", ".sh", ".json", ".md", ".cfg", ".ini", ".yaml", ".yml")
MARCADORES = (
    "tool-nth",
    "tool_nth",
    "TOOL-NTH",
    "pseUI",
    "BarraDeDepuracao",
    "SessaoDeDepuracao",
    "nth_debug_parada",
    "MarcadoresDoGutter",
)
PERMITIDOS = {os.path.abspath(SHIM)}

def _caminhos_de_fonte():
    raiz = os.path.abspath(RAIZ)
    tool = os.path.abspath(DIRETORIO_TOOL)
    for pasta, subpastas, arquivos in os.walk(raiz):
        caminho = os.path.abspath(pasta)
        if caminho == tool or caminho.startswith(tool + os.sep):
            subpastas[:] = []
            continue
        subpastas[:] = [nome for nome in subpastas if nome not in PASTAS_IGNORADAS]
        for nome in arquivos:
            if not nome.endswith(EXTENSOES):
                continue
            completo = os.path.abspath(os.path.join(pasta, nome))
            if completo in PERMITIDOS:
                continue
            yield completo

def _carregar(modulo, caminho):
    especimo = importlib.util.spec_from_file_location(modulo, caminho)
    instancia = importlib.util.module_from_spec(especimo)
    especimo.loader.exec_module(instancia)
    return instancia

def test_nenhum_arquivo_fora_da_pasta_cita_o_depurador():
    infratores = []
    for caminho in _caminhos_de_fonte():
        try:
            with open(caminho, "r", encoding="utf-8", errors="ignore") as handle:
                conteudo = handle.read()
        except OSError:
            continue
        for marcador in MARCADORES:
            if marcador in conteudo:
                infratores.append((os.path.relpath(caminho, RAIZ), marcador))
    assert not infratores, infratores

def test_shim_chama_o_plugin_real_quando_a_pasta_existe(capsys):
    shim = _carregar("plugins.tool_nth_presente", SHIM)
    ctx = AppContext()
    assert shim.setup(ctx) is None
    saida = capsys.readouterr().out
    assert "janela indisponível" in saida
    assert "pasta do depurador ausente" not in saida

def test_aplicacao_carrega_sem_a_pasta_do_depurador(capsys):
    escondido = DIRETORIO_TOOL + ".escondido"
    os.rename(DIRETORIO_TOOL, escondido)
    try:
        shim = _carregar("plugins.tool_nth_ausente", SHIM)
        ctx = AppContext()
        assert shim.setup(ctx) is None
        assert "pasta do depurador ausente" in capsys.readouterr().out

        aplicacao = _carregar("aplicacao_sem_depurador", os.path.join(RAIZ, "main.py"))
        aplicacao.load_plugins()
        aplicacao.load_external_plugins()
        contexto = AppContext()
        saida = capsys.readouterr().out
        assert "[PLUGIN] Falha ao carregar tool_nth.py" not in saida
        assert not any(type(item).__name__ == "Depurador" for item in contexto.external_plugins)
    finally:
        os.rename(escondido, DIRETORIO_TOOL)

def test_pasta_do_depurador_restaurada():
    assert os.path.isdir(DIRETORIO_TOOL)
    assert os.path.isfile(os.path.join(DIRETORIO_TOOL, "plugin.py"))
