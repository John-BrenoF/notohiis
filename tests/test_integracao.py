import importlib
import os

import pytest

from conftest import RAIZ
from utilidades import rodar_em_subprocesso

nativo = pytest.importorskip(
    "notohiis_core",
    reason="extensão nativa não compilada — rode core/native/build.sh",
)

SIMBOLOS = (
    ("main", "AppContext"),
    ("main", "AutocompleteEngine"),
    ("ui.control_panel", "AppContext"),
    ("ui.control_panel", "BufferManager"),
    ("ui.control_panel", "SessionManager"),
    ("ui.editor_area", "AppContext"),
    ("ui.editor_area", "FILE_CHANGED"),
    ("ui.file_name_search_panel", "AppContext"),
    ("ui.file_name_search_panel", "FileNameSearchResult"),
    ("ui.file_name_search_panel", "FileNameSearchService"),
    ("ui.global_search_panel", "AppContext"),
    ("ui.sidebar", "AppContext"),
    ("ui.sidebar", "BufferManager"),
    ("ui.sidebar", "FileManager"),
    ("ui.sidebar", "SessionManager"),
    ("ui.sidebar_context", "AppContext"),
    ("ui.sidebar_context", "FileManager"),
    ("ui.status_bar", "AppContext"),
    ("ui.status_bar", "GIT_STATUS_DEBOUNCE_MS"),
    ("ui.tab_bridge", "AppContext"),
    ("ui.tab_bridge", "BufferManager"),
    ("ui.tab_bridge", "TabManager"),
    ("ui.window", "AppContext"),
    ("ui.window", "SessionManager"),
    ("tui.editor_area", "AppContext"),
    ("tui.editor_area", "FILE_CHANGED"),
    ("tui.shortcuts", "AppContext"),
    ("tui.shortcuts", "BufferManager"),
    ("tui.sidebar", "AppContext"),
    ("tui.window", "AppContext"),
    ("tui.window", "SessionManager"),
    ("core.core_plugin.git_plugin", "AppContext"),
    ("core.core_plugin.git_plugin", "SessionManager"),
    ("core.core_plugin.git_plugin", "ThemeManager"),
    ("core.core_plugin.global_search_engine", "SEARCH_BATCH_SIZE"),
    ("core.core_plugin.terminal_plugin", "AppContext"),
    ("core.core_plugin.terminal_plugin", "THEME_CHANGED"),
    ("plugins.auto_close", "AppContext"),
    ("plugins.color_preview", "AppContext"),
    ("plugins.color_preview", "CONTENT_CHANGED"),
    ("plugins.image_viewer", "FILE_CHANGED"),
    ("plugins.video_player", "FILE_CHANGED"),
)


@pytest.mark.parametrize("nome_modulo,nome_simbolo", SIMBOLOS)
def test_modulo_importa_o_simbolo_do_core_nativo(nome_modulo, nome_simbolo):
    modulo = importlib.import_module(nome_modulo)
    assert getattr(modulo, nome_simbolo) is getattr(nativo, nome_simbolo), (
        f"{nome_modulo}.{nome_simbolo} não veio de notohiis_core"
    )


def test_raiz_do_projeto_aponta_para_o_repositorio():
    assert os.path.samefile(nativo.get_project_root(), RAIZ)


def test_aplicacao_inteira_sobe_em_processo_separado():
    codigo = (
        "import notohiis_core\n"
        "assert notohiis_core.is_native_core()\n"
        "import ui.window, ui.tab_bridge, ui.sidebar, ui.editor_area\n"
        "import tui.window\n"
        "import core.core_plugin.git_plugin, plugins.auto_close\n"
        "import main\n"
        "print('ok')\n"
    )
    resultado = rodar_em_subprocesso(codigo)
    assert resultado.returncode == 0, (
        f"processo falhou (código {resultado.returncode})\n"
        f"--- stdout ---\n{resultado.stdout}\n--- stderr ---\n{resultado.stderr}"
    )
    assert resultado.stdout.strip().endswith("ok")
