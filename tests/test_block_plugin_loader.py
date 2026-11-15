from block_plugin_loader import load_block_plugins
from conftest import RAIZ
from utilidades import rodar_em_subprocesso

PLUGIN_DEMO = (
    "class BlocoDemo:\n"
    "    def __init__(self, ctx):\n"
    "        self.ctx = ctx\n"
    "\n"
    "\n"
    "def setup(ctx):\n"
    "    ctx.external_plugins.append(BlocoDemo(ctx))\n"
)


class ContextoFake:
    def __init__(self):
        self.external_plugins = []


def _cria_bloco_python(pasta_plugins, nome_bloco, conteudo=PLUGIN_DEMO):
    bloco = pasta_plugins / nome_bloco
    bloco.mkdir()
    (bloco / "plugin.py").write_text(conteudo, encoding="utf-8")


def _cria_bloco_rust(pasta_plugins, nome_bloco, biblioteca=None):
    bloco = pasta_plugins / nome_bloco
    bloco.mkdir()
    (bloco / "Cargo.toml").write_text(
        '[package]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    if biblioteca is not None:
        (bloco / biblioteca).write_bytes(b"nao_e_uma_biblioteca_real")


def test_bloco_python_registra_no_contexto(tmp_path):
    contexto = ContextoFake()
    _cria_bloco_python(tmp_path, "NTH-demo")

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    assert len(contexto.external_plugins) == 1
    assert type(contexto.external_plugins[0]).__name__ == "BlocoDemo"


def test_pasta_de_blocos_ausente_nao_quebra(tmp_path):
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path / "nao_existe")

    assert contexto.external_plugins == []


def test_arquivos_avulsos_fora_de_bloco_sao_ignorados(tmp_path):
    (tmp_path / "avulso.py").write_text("raise SystemExit(9)\n", encoding="utf-8")
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    assert contexto.external_plugins == []


def test_bloco_quebrado_nao_impede_os_demais(tmp_path, capsys):
    _cria_bloco_python(tmp_path, "NTH-aaa-quebrado", "raise RuntimeError('estourou')\n")
    _cria_bloco_python(tmp_path, "NTH-zzz-bom")
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    assert len(contexto.external_plugins) == 1
    assert type(contexto.external_plugins[0]).__name__ == "BlocoDemo"
    assert "[BLOCO] Falha ao carregar NTH-aaa-quebrado" in capsys.readouterr().out


def test_bloco_sem_estrutura_reconhecida(tmp_path, capsys):
    (tmp_path / "NTH-vazio").mkdir()
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    assert contexto.external_plugins == []
    assert "[BLOCO] Falha ao carregar NTH-vazio" in capsys.readouterr().out


def test_bloco_rust_sem_biblioteca_compilada(tmp_path, capsys):
    _cria_bloco_rust(tmp_path, "NTH-rust")
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    assert contexto.external_plugins == []
    assert "extensão Rust não compilada" in capsys.readouterr().out


def test_bloco_rust_com_biblioteca_compilada_tenta_carregar(tmp_path, capsys):
    _cria_bloco_rust(tmp_path, "NTH-rust", biblioteca="demo.abi3.so")
    contexto = ContextoFake()

    load_block_plugins(contexto, pasta_plugins=tmp_path)

    saida = capsys.readouterr().out
    assert "extensão Rust não compilada" not in saida
    assert "[BLOCO] Falha ao carregar NTH-rust" in saida


def test_main_carrega_blocos_apos_plugins_avulsos():
    codigo = (
        "import importlib.util\n"
        "import main\n"
        "importlib.util.spec_from_file_location = lambda *args, **kwargs: None\n"
        "chamadas = []\n"
        "main.load_block_plugins = lambda ctx: chamadas.append(ctx)\n"
        "main.load_external_plugins()\n"
        "print('CHAMOU' if chamadas else 'NAO_CHAMOU')\n"
    )
    resultado = rodar_em_subprocesso(codigo, cwd=RAIZ)

    assert resultado.returncode == 0, resultado.stderr
    assert "CHAMOU" in resultado.stdout
    assert "NAO_CHAMOU" not in resultado.stdout
