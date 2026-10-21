import os
import threading

import pytest

from conftest import RAIZ
from utilidades import EditorFake

native = pytest.importorskip(
    "notohiis_core",
    reason="extensão nativa não compilada — rode core/native/build.sh",
)


@pytest.fixture
def contexto():
    from notohiis_core import AppContext

    ctx = AppContext()
    yield ctx
    ctx.editor = None
    ctx.status_bar = None
    ctx.window = None
    ctx.sidebar = None
    ctx.current_file = None
    ctx.project_root = None
    ctx.set_theme({}, None)


@pytest.fixture
def raiz_nativa(tmp_path):
    anterior = native.get_project_root()
    native.set_project_root(str(tmp_path))
    yield tmp_path
    native.set_project_root(anterior)


def test_extensao_esta_ativa():
    assert native.is_native_core() is True
    assert os.path.isfile(native.__file__) or os.path.islink(native.__file__)
    assert os.path.isdir(RAIZ)


def test_project_root_nativo_e_a_raiz_do_repositorio():
    assert os.path.samefile(native.get_project_root(), RAIZ)


def test_eventbus_on_off_emit():
    bus = native.EventBus()
    vistos = []

    def ouvir(payload):
        vistos.append(payload)

    bus.on("evt", ouvir)
    bus.emit("evt", 42)
    bus.emit("evt")
    bus.off("evt", ouvir)
    bus.emit("evt", 7)
    assert vistos == [42, None]


def test_constantes_de_eventos_no_modulo():
    assert native.DIRTY_CHANGED == "dirty_changed"
    assert native.THEME_CHANGED == "theme_changed"
    assert native.FILE_CHANGED == "file_changed"
    assert native.CONTENT_CHANGED == "content_changed"
    assert native.LINE_NUMBERS_REDRAWN == "line_numbers_redrawn"


def test_app_context_e_singleton(contexto):
    from notohiis_core import AppContext

    assert AppContext() is AppContext()
    assert AppContext() is contexto


def test_app_context_expoe_os_slots_padrao(contexto):
    assert contexto.tab_manager is None
    assert contexto.tab_bridge is None
    assert contexto.autocomplete_engine is None
    assert contexto.external_plugins == []
    assert contexto.smart_tab_hiding is True
    assert contexto.sidebar_tree_navigation is False
    assert isinstance(contexto.theme, dict)
    assert contexto.events is not None
    assert contexto.edit_history is not None
    with pytest.raises(AttributeError):
        contexto.atributo_que_nao_existe


def test_app_context_guarda_atributos_genericos(contexto):
    contexto.qualquer_coisa = 42
    assert contexto.qualquer_coisa == 42


def test_set_theme_atualiza_e_notifica(contexto):
    vistos = []
    contexto.events.on("theme_changed", vistos.append)
    try:
        contexto.set_theme({"bg": "#000"}, "/x/y/azul.json")
        assert contexto.theme == {"bg": "#000"}
        assert contexto.selected_theme == "azul"
        assert vistos == [{"bg": "#000"}]

        contexto.set_theme(None, None)
        assert contexto.theme == {}
        assert contexto.selected_theme is None
    finally:
        contexto.events.off("theme_changed", vistos.append)


def test_is_dirty_espelha_o_historico(contexto):
    contexto.is_dirty = True
    assert contexto.is_dirty is True
    contexto.is_dirty = False
    assert contexto.is_dirty is False


def test_dirty_fluxo_completo_com_editor(contexto):
    editor = EditorFake("abc")
    contexto.set_editor(editor)

    eventos = []
    contexto.events.on("dirty_changed", eventos.append)
    try:
        contexto.edit_history.on_content_loaded("abc")
        assert contexto.is_dirty is False
        assert editor.resets == 1

        editor.text = "abcd"
        contexto.handle_typing("d")
        assert contexto.is_dirty is True

        contexto.notify_save()
        assert contexto.is_dirty is False
    finally:
        contexto.events.off("dirty_changed", eventos.append)

    assert eventos == [True, False]


def test_transacoes_agrupam_no_editor(contexto):
    editor = EditorFake("")
    contexto.set_editor(editor)

    contexto.begin_transaction()
    contexto.begin_transaction()
    assert contexto.edit_history.is_in_transaction is True
    contexto.end_transaction()
    assert contexto.edit_history.is_in_transaction is True
    contexto.end_transaction()
    assert contexto.edit_history.is_in_transaction is False
    assert editor.grupos == ["begin", "end"]


def test_undo_e_redo_chamam_o_editor(contexto):
    editor = EditorFake("abc")
    contexto.set_editor(editor)
    contexto.perform_undo()
    contexto.perform_redo()
    assert editor.undos == 1
    assert editor.redos == 1


def test_edit_history_separadores_logicos_e_de_15_caracteres():
    from notohiis_core import EditHistoryManager

    eventos = native.EventBus()
    gerente = EditHistoryManager(eventos)
    editor = EditorFake("abc")
    gerente.attach_editor(editor)

    gerente.on_content_loaded("abc")
    assert not gerente.is_dirty

    for caractere in "abc":
        gerente.on_text_input(caractere)
    assert editor.separadores == 0

    gerente.on_text_input(".")
    assert editor.separadores == 1

    for _ in range(15):
        gerente.on_text_input("x")
    assert editor.separadores == 2


def test_edit_history_emite_eventos_de_sujeira():
    from notohiis_core import EditHistoryManager

    eventos = native.EventBus()
    gerente = EditHistoryManager(eventos)
    gerente.attach_editor(EditorFake("abc"))

    vistos = []
    eventos.on("dirty_changed", vistos.append)
    gerente.on_content_loaded("abc")
    gerente.set_dirty(True)
    gerente.mark_saved("abc")
    gerente.set_dirty(True)
    assert vistos == [True, False, True]


def test_edit_history_sem_editor_nao_faz_nada():
    from notohiis_core import EditHistoryManager

    gerente = EditHistoryManager(native.EventBus())
    gerente.on_text_input("a")
    gerente.perform_undo()
    gerente.perform_redo()
    gerente.begin_transaction()
    gerente.end_transaction()
    assert not gerente.is_dirty
    assert not gerente.is_in_transaction


def test_edit_history_nao_reentra_durante_undo():
    from notohiis_core import EditHistoryManager

    gerente = EditHistoryManager(native.EventBus())
    editor = EditorFake("abc")
    gerente.attach_editor(editor)

    entradas = []

    def desfazer():
        entradas.append(1)
        gerente.on_text_input("z")

    editor.undo = desfazer
    gerente.perform_undo()
    assert entradas == [1]
    assert editor.separadores == 0


def test_tab_construtor_aceita_kwargs():
    from notohiis_core import Tab

    tab = Tab(id=7, path="/x/y.txt", content="c", title="t", is_dirty=True)
    assert (tab.id, tab.path, tab.content, tab.title, tab.is_dirty) == (
        7, "/x/y.txt", "c", "t", True,
    )
    assert tab.display_name == "y.txt"
    assert Tab(id=8).display_name == "Novo Arquivo"


def test_tab_manager_abre_seleciona_e_fecha(tmp_path):
    from notohiis_core import TabManager

    arquivo = tmp_path / "nota.md"
    arquivo.write_text("# olá\n", encoding="utf-8")

    gerente = TabManager()
    tab = gerente.open_file(str(arquivo))
    assert tab.title == "nota.md"
    assert tab.display_name == "nota.md"
    assert tab.content == "# olá\n"
    assert not tab.is_dirty
    assert gerente.get_active_tab() is tab
    assert gerente.find_tab_by_path(str(arquivo)) is tab

    assert gerente.open_file(str(arquivo)) is tab
    assert len(gerente.get_tabs()) == 1

    outro = gerente.create_tab()
    assert outro.id != tab.id
    assert gerente.get_active_tab() is outro

    gerente.update_active_content("mudou")
    assert outro.is_dirty
    assert not gerente.close_tab(outro.id)
    assert gerente.close_tab(outro.id, force=True)
    assert gerente.get_active_tab() is tab

    assert gerente.close_tab(tab.id)
    assert gerente.get_tabs() == []
    assert gerente.active_tab_id is None
    assert gerente.close_tab(tab.id)


def test_tab_manager_atualiza_conteudo_e_caminho(tmp_path):
    from notohiis_core import TabManager

    gerente = TabManager()
    tab = gerente.create_tab()
    gerente.update_active_content("primeira")
    assert tab.content == "primeira" and tab.is_dirty
    gerente.update_active_content("primeira")
    assert tab.is_dirty

    destino = tmp_path / "pasta" / "renomeado.txt"
    gerente.update_tab_path(tab.id, str(destino))
    assert tab.path == str(destino)
    assert tab.title == "renomeado.txt"
    assert tab.display_name == "renomeado.txt"


def test_tab_manager_salva_aba_ativa(tmp_path):
    from notohiis_core import TabManager

    gerente = TabManager()
    tab = gerente.create_tab()
    gerente.update_active_content("conteúdo")
    assert gerente.save_active_tab() is False

    destino = tmp_path / "sub" / "arquivo.txt"
    gerente.update_tab_path(tab.id, str(destino))
    assert gerente.save_active_tab() is True
    assert destino.read_text(encoding="utf-8") == "conteúdo"
    assert not tab.is_dirty


def test_buffer_manager_roundtrip(tmp_path):
    from notohiis_core import BufferManager

    alvo = tmp_path / "a" / "b" / "nota.md"
    assert BufferManager.save_file(str(alvo), "# olá\n")
    assert alvo.read_text(encoding="utf-8") == "# olá\n"
    assert BufferManager.read_file(str(alvo)) == "# olá\n"
    assert BufferManager.get_file_extension(str(alvo)) == ".md"

    assert BufferManager.read_file(str(tmp_path / "nao_existe.txt")) == ""

    binario = tmp_path / "imagem.png"
    binario.write_bytes(b"\x00\x01\x02")
    assert BufferManager.read_file(str(binario)) == ""


def test_buffer_manager_sem_diretorio_retorna_falso(tmp_path, monkeypatch):
    from notohiis_core import BufferManager

    monkeypatch.chdir(tmp_path)
    assert BufferManager.save_file("soltinho.txt", "x") is False
    assert not (tmp_path / "soltinho.txt").exists()


def test_file_manager_lista_e_ordena_pastas_primeiro(tmp_path):
    from notohiis_core import FileManager

    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "zeta.txt").write_text("z", encoding="utf-8")
    (tmp_path / "Alfa.txt").write_text("a", encoding="utf-8")

    itens = FileManager.list_directory(str(tmp_path))
    assert [item["name"] for item in itens] == ["docs", "src", "Alfa.txt", "zeta.txt"]
    assert [item["is_dir"] for item in itens] == [True, True, False, False]
    assert itens[0]["path"] == str(tmp_path / "docs")

    assert FileManager.list_directory(str(tmp_path / "docs")) == []
    assert FileManager.list_directory(str(tmp_path / "nao_existe")) == []
    assert FileManager.list_directory("") == []


def test_file_manager_criar_renomear_excluir(tmp_path):
    from notohiis_core import FileManager

    alvo = tmp_path / "pasta" / "arquivo.txt"
    assert FileManager.create_file(str(alvo))
    assert alvo.exists() and alvo.read_text(encoding="utf-8") == ""

    assert FileManager.create_directory(str(tmp_path / "a" / "b"))
    assert (tmp_path / "a" / "b").is_dir()

    assert FileManager.rename_path(str(alvo), "renomeado.txt")
    assert (tmp_path / "pasta" / "renomeado.txt").exists()
    assert not alvo.exists()

    assert FileManager.delete_path(str(tmp_path / "pasta" / "renomeado.txt"))
    assert FileManager.delete_path(str(tmp_path / "a"))
    assert not FileManager.delete_path(str(tmp_path / "nao_existe.txt"))


def test_file_manager_constantes_do_dialogo():
    from notohiis_core import FileManager

    assert FileManager.SYSTEM_PYTHON == "/usr/bin/python3"
    assert FileManager.SYSTEM_DIALOG_TIMEOUT == 300
    assert "gi.repository" in FileManager.SYSTEM_DIALOG_SCRIPT


def test_session_roundtrip_de_projeto_recente(tmp_path, monkeypatch):
    from notohiis_core import SessionManager

    monkeypatch.chdir(tmp_path)
    assert SessionManager.SESSION_FILE == ".session_config"
    assert SessionManager.MAX_RECENT == 10
    assert SessionManager.load_session() is None

    raiz = str(tmp_path)
    SessionManager.save_session(raiz)
    assert SessionManager.load_session() == raiz

    for indice in range(15):
        SessionManager.save_session(str(tmp_path / f"p{indice}"))
    recentes = SessionManager.get_recent_projects()
    assert len(recentes) == 10
    assert recentes[0].endswith("p14")

    SessionManager.save_session(raiz)
    recentes = SessionManager.get_recent_projects()
    assert recentes[0] == raiz
    assert recentes.count(raiz) == 1

    SessionManager.save_session(None)
    assert SessionManager.load_session() == str(tmp_path)


def test_preferencias_de_tema_e_ui(raiz_nativa):
    from notohiis_core import SessionManager

    pref = raiz_nativa / "ui" / "preferencias" / "preferecia.json"
    assert os.path.normpath(SessionManager.get_pref_path()) == os.path.normpath(str(pref))

    assert SessionManager.load_theme_pref() == "editor"
    SessionManager.save_theme_pref("claro.json")
    assert SessionManager.load_theme_pref() == "claro.json"

    assert SessionManager.get_ui_setting("sidebar_width", 250) == 250
    SessionManager.set_ui_setting("sidebar_width", 123)
    assert SessionManager.get_ui_setting("sidebar_width", 250) == 123
    assert SessionManager.get_ui_setting("nao_existe", "padrao") == "padrao"

    prefs = SessionManager.load_preferences()
    assert prefs["ui"]["sidebar_width"] == 123
    prefs["marca"] = 1
    SessionManager.save_preferences(prefs)
    assert SessionManager.load_preferences()["marca"] == 1


def test_theme_manager_lista_resolve_e_carrega(raiz_nativa):
    from notohiis_core import ThemeManager

    estilo = raiz_nativa / "ui" / "estilo"
    estilo.mkdir(parents=True)
    (estilo / "editor.json").write_text('{"bg": "#111"}', encoding="utf-8")
    (estilo / "claro.json").write_text('{"bg": "#fff"}', encoding="utf-8")
    (estilo / "nao_e_tema.txt").write_text("ignorar", encoding="utf-8")

    assert ThemeManager.list_themes() == ["claro.json", "editor.json"]
    assert ThemeManager.get_theme_display_list() == ["claro", "editor"]
    assert os.path.normpath(ThemeManager.get_theme_dir()) == os.path.normpath(str(estilo))
    assert os.path.normpath(ThemeManager.resolve_theme_path("claro")) == str(
        estilo / "claro.json"
    )
    assert os.path.normpath(ThemeManager.resolve_theme_path("claro.json")) == str(
        estilo / "claro.json"
    )
    assert os.path.normpath(ThemeManager.resolve_theme_path(None)) == str(
        estilo / "editor.json"
    )

    assert ThemeManager.load_theme("claro")["bg"] == "#fff"
    assert ThemeManager.load_theme("claro.json")["bg"] == "#fff"
    assert ThemeManager.load_theme("nao_existe")["bg"] == "#fff"
    assert ThemeManager.get_theme_name("/x/y/azul.json") == "azul"
    assert ThemeManager.get_theme_name(None) == "editor"


def test_theme_manager_sem_nenhum_tema(raiz_nativa):
    from notohiis_core import ThemeManager

    assert ThemeManager.list_themes() == []
    assert ThemeManager.get_theme_display_list() == []
    assert ThemeManager.load_theme() == {}


@pytest.fixture
def arvore_de_busca(tmp_path):
    (tmp_path / "Nota.md").write_text("", encoding="utf-8")
    (tmp_path / "outro.txt").write_text("", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notarial.txt").write_text("", encoding="utf-8")
    (tmp_path / "pasta_notas").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "nota_dentro_do_git.md").write_text("", encoding="utf-8")
    return tmp_path


def _buscar(servico, consulta, raiz, timeout=20):
    lotes = []
    total = []
    concluido = threading.Event()

    def on_result(lote):
        lotes.append(list(lote))

    def on_done(quantidade):
        total.append(quantidade)
        concluido.set()

    servico.search_async(consulta, raiz, on_result, on_done)
    assert concluido.wait(timeout), "busca não concluiu a tempo"
    return lotes, total


def test_file_name_search_assincrono_e_ignora_diretorios(arvore_de_busca):
    from notohiis_core import FileNameSearchService

    servico = FileNameSearchService()
    lotes, total = _buscar(servico, "NoTa", str(arvore_de_busca))

    achados = [resultado for lote in lotes for resultado in lote]
    assert sorted(resultado.name for resultado in achados) == [
        "Nota.md",
        "notarial.txt",
        "pasta_notas",
    ]
    assert total == [3]
    assert all(len(lote) <= 30 for lote in lotes)
    assert achados[0].path.startswith(str(arvore_de_busca))

    diretorios = [r.is_directory for r in achados if r.name == "pasta_notas"]
    assert diretorios == [True]
    arquivos = [r.is_directory for r in achados if r.name == "Nota.md"]
    assert arquivos == [False]


def test_file_name_search_com_consulta_vazia_conclui_com_zero(arvore_de_busca):
    from notohiis_core import FileNameSearchService

    servico = FileNameSearchService()
    lotes, total = _buscar(servico, "   ", str(arvore_de_busca))
    assert lotes == [[]]
    assert total == [0]


def test_file_name_search_com_raiz_inexistente(arvore_de_busca):
    from notohiis_core import FileNameSearchService

    servico = FileNameSearchService()
    lotes, total = _buscar(servico, "nota", str(arvore_de_busca / "nao_existe"))
    assert total == [0]


def test_file_name_search_resultado_e_imutavel():
    from notohiis_core import FileNameSearchResult

    resultado = FileNameSearchResult(path="/a/b.txt", name="b.txt", is_directory=False)
    assert (resultado.path, resultado.name, resultado.is_directory) == (
        "/a/b.txt", "b.txt", False,
    )
    with pytest.raises(Exception):
        resultado.name = "outro"


@pytest.fixture(scope="module")
def motor():
    from notohiis_core import AutocompleteEngine

    return AutocompleteEngine()


def test_autocomplete_base_de_sugestoes_espelha_o_python(motor):
    import keyword

    esperado = sorted(set(keyword.kwlist + [
        "print", "range", "len", "input", "int", "str", "list",
        "dict", "set", "tuple", "enumerate", "zip", "open", "self", "cls",
        "append", "extend", "split", "join",
    ]))
    assert motor.suggestions_base == esperado
    assert motor.lsp is not None
    assert motor.initialized in (True, False)


def test_autocomplete_fallback_local(motor):
    assert motor.get_local_fallback("x = pri", 1, 6) == ["print"]
    assert motor.get_local_fallback("enu|merable", 1, 3) == ["enumerate"]
    assert motor.get_local_fallback("", 1, 0) == []
    assert motor.get_local_fallback("x = 1", 1, 5) == []
    assert motor.get_local_fallback("uma\nduas\npri", 5, 3) == []
    assert motor.get_local_fallback("x = Pri", 1, 6) == []


def test_autocomplete_request_completion_sem_arquivo_usa_fallback(motor, contexto):
    editor = EditorFake("x = pri")
    contexto.set_editor(editor)
    contexto.current_file = None

    recebidos = []
    motor.request_completion(1, 6, recebidos.append)
    assert recebidos == [["print"]]


def test_ui_e_plugins_importam_com_core_nativo():
    import importlib

    modulos = (
        "core.interfaces",
        "core.core_plugin.git_plugin",
        "core.core_plugin.global_search_engine",
        "core.core_plugin.markdown_viewer",
        "core.core_plugin.python_syntax",
        "core.core_plugin.terminal_plugin",
        "plugins.auto_close",
        "plugins.color_preview",
        "plugins.icon_notohiis",
        "tui.editor_area",
        "tui.shortcuts",
        "tui.window",
        "ui.control_panel",
        "ui.editor_area",
        "ui.file_name_search_panel",
        "ui.global_search_panel",
        "ui.search_base",
        "ui.shortcuts",
        "ui.sidebar",
        "ui.sidebar_context",
        "ui.status_bar",
        "ui.tab_bridge",
        "ui.window",
    )
    for nome in modulos:
        try:
            importlib.import_module(nome)
        except ImportError as erro:
            dependencia = (erro.name or "").split(".")[0]
            if dependencia in {"core", "ui", "tui", "plugins"}:
                raise
            pytest.skip(f"{nome} pede dependência opcional ausente: {erro.name}")
