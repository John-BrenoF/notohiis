use std::collections::HashMap;
use std::sync::Mutex;

use pyo3::exceptions::{PyAttributeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
use pyo3::types::{PyBool, PyDict, PyList};

use crate::edit_history::EditHistoryManager;
use crate::events::{EventBus, DIRTY_CHANGED, THEME_CHANGED};
use crate::runtime;

static INSTANCIA: PyOnceLock<Py<AppContext>> = PyOnceLock::new();

#[pyclass]
pub struct AppContext {
    slots: Mutex<HashMap<String, Py<PyAny>>>,
    eventos: Mutex<Py<EventBus>>,
    historico: Mutex<Py<EditHistoryManager>>,
}

impl AppContext {
    pub fn criar_ou_obter(py: Python<'_>) -> PyResult<Py<AppContext>> {
        if let Some(instancia) = INSTANCIA.get(py) {
            return Ok(instancia.clone_ref(py));
        }

        let mut slots = HashMap::new();
        for nome in [
            "window",
            "editor",
            "sidebar",
            "status_bar",
            "current_file",
            "project_root",
            "git_plugin",
            "md_plugin",
            "py_plugin",
            "selected_theme",
            "autocomplete_engine",
            "global_search_engine",
            "tab_manager",
            "tab_bridge",
            "search_bar",
            "replace_bar",
        ] {
            slots.insert(nome.to_string(), py.None());
        }
        slots.insert("theme".to_string(), PyDict::new(py).unbind().into_any());
        slots.insert(
            "external_plugins".to_string(),
            PyList::empty(py).unbind().into_any(),
        );
        slots.insert(
            "smart_tab_hiding".to_string(),
            PyBool::new(py, true).to_owned().into_any().unbind(),
        );
        slots.insert(
            "sidebar_tree_navigation".to_string(),
            PyBool::new(py, false).to_owned().into_any().unbind(),
        );

        let eventos = Py::new(py, EventBus::novo())?;
        let historico =
            Py::new(py, EditHistoryManager::novo(eventos.clone_ref(py).into_any()))?;
        let contexto = Py::new(
            py,
            AppContext {
                slots: Mutex::new(slots),
                eventos: Mutex::new(eventos.clone_ref(py)),
                historico: Mutex::new(historico),
            },
        )?;
        let _ = INSTANCIA.set(py, contexto.clone_ref(py));

        let callback = contexto.bind(py).getattr("_on_dirty_changed")?.unbind();
        eventos.borrow(py).registrar(DIRTY_CHANGED, callback);

        Ok(contexto)
    }

    pub fn slot(&self, py: Python<'_>, nome: &str) -> PyResult<Option<Py<PyAny>>> {
        let slots = self.slots.lock().unwrap();
        Ok(slots.get(nome).map(|valor| valor.clone_ref(py)))
    }

    fn eventos(&self, py: Python<'_>) -> Py<EventBus> {
        self.eventos.lock().unwrap().clone_ref(py)
    }

    fn historico(&self, py: Python<'_>) -> Py<EditHistoryManager> {
        self.historico.lock().unwrap().clone_ref(py)
    }

    fn atualizar_status_sujeira(&self, py: Python<'_>) -> PyResult<()> {
        let Some(status_bar) = self.slot(py, "status_bar")? else {
            return Ok(());
        };
        let Some(editor) = self.slot(py, "editor")? else {
            return Ok(());
        };
        if !status_bar.bind(py).is_truthy()? || !editor.bind(py).is_truthy()? {
            return Ok(());
        }

        let arquivo = self.slot(py, "current_file")?;
        let indice: String = editor.call_method0(py, "get_cursor_index")?.extract(py)?;
        let partes: Vec<&str> = indice.split('.').collect();
        if partes.len() != 2 {
            return Err(PyValueError::new_err("not enough values to unpack"));
        }
        let linha: i64 = partes[0]
            .parse()
            .map_err(|_| PyValueError::new_err("invalid literal for int()"))?;
        let coluna: i64 = partes[1]
            .parse()
            .map_err(|_| PyValueError::new_err("invalid literal for int()"))?;

        let nome_arquivo = match arquivo {
            Some(arquivo) if arquivo.bind(py).is_truthy()? => arquivo.extract::<String>(py)?,
            _ => "Novo Arquivo".to_string(),
        };

        status_bar.call_method1(py, "update_status", (linha, coluna, nome_arquivo))?;
        Ok(())
    }
}

#[pymethods]
impl AppContext {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Py<Self>> {
        Self::criar_ou_obter(py)
    }

    #[getter]
    fn is_dirty(&self, py: Python<'_>) -> bool {
        self.historico(py).borrow(py).sujeira()
    }

    #[getter]
    fn events(&self, py: Python<'_>) -> Py<EventBus> {
        self.eventos(py)
    }

    #[getter]
    fn edit_history(&self, py: Python<'_>) -> Py<EditHistoryManager> {
        self.historico(py)
    }

    fn __getattr__(&self, py: Python<'_>, nome: &str) -> PyResult<Py<PyAny>> {
        match nome {
            "events" => Ok(self.eventos(py).into_any()),
            "edit_history" => Ok(self.historico(py).into_any()),
            _ => {
                let slots = self.slots.lock().unwrap();
                match slots.get(nome) {
                    Some(valor) => Ok(valor.clone_ref(py)),
                    None => Err(PyAttributeError::new_err(nome.to_string())),
                }
            }
        }
    }

    fn __setattr__(&self, py: Python<'_>, nome: &str, valor: Py<PyAny>) -> PyResult<()> {
        match nome {
            "is_dirty" => self
                .historico(py)
                .borrow(py)
                .definir_sujeira(py, valor.extract(py)?),
            "events" => {
                *self.eventos.lock().unwrap() = valor.extract(py)?;
                Ok(())
            }
            "edit_history" => {
                *self.historico.lock().unwrap() = valor.extract(py)?;
                Ok(())
            }
            _ => {
                self.slots.lock().unwrap().insert(nome.to_string(), valor);
                Ok(())
            }
        }
    }

    fn set_window(&self, py: Python<'_>, window: Py<PyAny>) -> PyResult<()> {
        self.__setattr__(py, "window", window)
    }

    fn set_editor(&self, py: Python<'_>, editor: Py<PyAny>) -> PyResult<()> {
        self.__setattr__(py, "editor", editor.clone_ref(py))?;
        self.historico(py).borrow(py).anexar_editor(editor);
        Ok(())
    }

    fn set_sidebar(&self, py: Python<'_>, sidebar: Py<PyAny>) -> PyResult<()> {
        self.__setattr__(py, "sidebar", sidebar)
    }

    fn set_status_bar(&self, py: Python<'_>, status_bar: Py<PyAny>) -> PyResult<()> {
        self.__setattr__(py, "status_bar", status_bar)
    }

    #[pyo3(signature = (theme, theme_name = None))]
    fn set_theme(
        &self,
        py: Python<'_>,
        theme: Py<PyAny>,
        theme_name: Option<String>,
    ) -> PyResult<()> {
        let tema = if theme.bind(py).is_truthy()? {
            theme
        } else {
            PyDict::new(py).unbind().into_any()
        };
        self.__setattr__(py, "theme", tema.clone_ref(py))?;

        let selecionado = theme_name
            .filter(|nome| !nome.is_empty())
            .map(|nome| {
                let base = runtime::basename(&nome);
                match std::path::Path::new(&base).file_stem() {
                    Some(stem) => stem.to_string_lossy().into_owned(),
                    None => String::new(),
                }
            });
        self.__setattr__(
            py,
            "selected_theme",
            match selecionado {
                Some(nome) => nome.into_pyobject(py)?.into_any().unbind(),
                None => py.None(),
            },
        )?;

        self.eventos(py)
            .borrow(py)
            .emitir(py, THEME_CHANGED, Some(tema))
    }

    fn notify_save(&self, py: Python<'_>) -> PyResult<()> {
        match self.slot(py, "editor")? {
            Some(editor) if editor.bind(py).is_truthy()? => {
                let texto: String = editor.call_method0(py, "get_text")?.extract(py)?;
                self.historico(py).borrow(py).marcar_salvo(py, texto)
            }
            _ => Ok(()),
        }
    }

    fn handle_typing(&self, py: Python<'_>, char: Option<String>) -> PyResult<()> {
        self.historico(py).borrow(py).entrada_texto(py, char)
    }

    fn begin_transaction(&self, py: Python<'_>) -> PyResult<()> {
        self.historico(py).borrow(py).iniciar_transacao(py)
    }

    fn end_transaction(&self, py: Python<'_>) -> PyResult<()> {
        self.historico(py).borrow(py).finalizar_transacao(py)
    }

    fn perform_undo(&self, py: Python<'_>) -> PyResult<()> {
        self.historico(py).borrow(py).desfazer(py)
    }

    fn perform_redo(&self, py: Python<'_>) -> PyResult<()> {
        self.historico(py).borrow(py).refazer(py)
    }

    fn _on_dirty_changed(&self, py: Python<'_>, _dirty: bool) -> PyResult<()> {
        self.atualizar_status_sujeira(py)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AppContext>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    fn contexto(py: Python<'_>) -> Py<AppContext> {
        AppContext::criar_ou_obter(py).unwrap()
    }

    fn serializado() -> std::sync::MutexGuard<'static, ()> {
        crate::teste_util::lock_global()
    }

    #[test]
    fn singleton_devolve_sempre_a_mesma_instancia() {
        let _guarda = serializado();
        Python::attach(|py| {
            let a = contexto(py);
            let b = contexto(py);
            assert_eq!(a.as_ptr(), b.as_ptr());
            assert_eq!(
                a.as_ptr(),
                AppContext::criar_ou_obter(py).unwrap().as_ptr()
            );
        });
    }

    #[test]
    fn slots_padrao_existem_e_sao_none() {
        let _guarda = serializado();
        Python::attach(|py| {
            let ctx = contexto(py);
            for nome in ["md_plugin", "py_plugin", "git_plugin", "global_search_engine", "autocomplete_engine", "search_bar", "replace_bar"] {
                let valor = ctx.borrow(py).slot(py, nome).unwrap();
                let valor = valor.expect(&format!("slot {} deveria existir", nome));
                assert!(valor.bind(py).is_none(), "slot {} deveria valer None", nome);
            }
            let externos = ctx.borrow(py).slot(py, "external_plugins").unwrap().unwrap();
            assert!(externos.bind(py).is_instance_of::<pyo3::types::PyList>());
        });
    }

    #[test]
    fn atributos_genericos_guardam_e_devolvem_valores() {
        let _guarda = serializado();
        Python::attach(|py| {
            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            let valor = 42i64.into_pyobject(py).unwrap().to_owned().into_any().unbind();
            ref_ctx.__setattr__(py, "qualquer_coisa", valor.clone_ref(py)).unwrap();
            let lido = ref_ctx.__getattr__(py, "qualquer_coisa").unwrap();
            assert_eq!(lido.extract::<i64>(py).unwrap(), 42);
            let erro = ref_ctx.__getattr__(py, "nao_existe_nunca");
            assert!(erro.is_err());
        });
    }

    #[test]
    fn flags_padrao_de_ui_estao_definidas() {
        let _guarda = serializado();
        Python::attach(|py| {
            let ctx = contexto(py);
            let smart = ctx.borrow(py).slot(py, "smart_tab_hiding").unwrap().unwrap();
            assert!(smart.extract::<bool>(py).unwrap());
            let tree = ctx.borrow(py).slot(py, "sidebar_tree_navigation").unwrap().unwrap();
            assert!(!tree.extract::<bool>(py).unwrap());
        });
    }

    #[test]
    fn set_theme_atualiza_tema_e_notifica_listeners() {
        let _guarda = serializado();
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "vistos = []\ndef ouvir(tema): vistos.append(tema)",
            );
            let escopo = escopo.bind(py);
            let ouvir = escopo.get_item("ouvir").unwrap().unwrap();
            let vistos = escopo.get_item("vistos").unwrap().unwrap();

            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            let eventos = ref_ctx.eventos(py);
            eventos.borrow(py).registrar(THEME_CHANGED, ouvir.unbind());

            let tema = PyDict::new(py);
            tema.set_item("bg", "#000").unwrap();
            ref_ctx
                .set_theme(py, tema.clone().unbind().into_any(), Some("/x/y/azul.json".to_string()))
                .unwrap();

            let selecionado = ref_ctx.slot(py, "selected_theme").unwrap().unwrap();
            assert_eq!(selecionado.extract::<String>(py).unwrap(), "azul");
            assert!(vistos.cast::<pyo3::types::PyList>().unwrap().len() == 1);
        });
    }

    #[test]
    fn set_theme_vazio_vira_dict_e_selected_none() {
        let _guarda = serializado();
        Python::attach(|py| {
            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            let tema = PyDict::new(py);
            tema.set_item("bg", "#fff").unwrap();
            ref_ctx
                .set_theme(py, tema.unbind().into_any(), Some("qualquer.json".to_string()))
                .unwrap();
            ref_ctx.set_theme(py, py.None(), None).unwrap();
            let tema = ref_ctx.slot(py, "theme").unwrap().unwrap();
            assert!(tema.bind(py).is_instance_of::<PyDict>());
            let selecionado = ref_ctx.slot(py, "selected_theme").unwrap().unwrap();
            assert!(selecionado.bind(py).is_none());
        });
    }

    #[test]
    fn notify_save_com_editor_marca_como_limpo() {
        let _guarda = serializado();
        Python::attach(|py| {
            let editor = crate::teste_util::editor_falso(py, "conteúdo salvo");
            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            ref_ctx.set_editor(py, editor).unwrap();
            ref_ctx.historico(py).borrow(py).definir_sujeira(py, true).unwrap();
            assert!(ref_ctx.is_dirty(py));
            ref_ctx.notify_save(py).unwrap();
            assert!(!ref_ctx.is_dirty(py));
        });
    }

    #[test]
    fn is_dirty_espelha_o_historico() {
        let _guarda = serializado();
        Python::attach(|py| {
            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            ref_ctx.__setattr__(py, "is_dirty", PyBool::new(py, true).to_owned().into_any().unbind()).unwrap();
            assert!(ref_ctx.is_dirty(py));
            ref_ctx.__setattr__(py, "is_dirty", PyBool::new(py, false).to_owned().into_any().unbind()).unwrap();
            assert!(!ref_ctx.is_dirty(py));
        });
    }

    #[test]
    fn set_editor_anexa_ao_historico_para_transacoes() {
        let _guarda = serializado();
        Python::attach(|py| {
            let editor = crate::teste_util::editor_falso(py, "");
            let ctx = contexto(py);
            let ref_ctx = ctx.borrow(py);
            ref_ctx.set_editor(py, editor.clone_ref(py)).unwrap();
            ref_ctx.begin_transaction(py).unwrap();
            assert!(ref_ctx.edit_history(py).borrow(py).em_transacao());
            ref_ctx.end_transaction(py).unwrap();
            assert!(!ref_ctx.edit_history(py).borrow(py).em_transacao());
            let grupos = editor.getattr(py, "grupos").unwrap();
            let grupos: Vec<String> = grupos.extract(py).unwrap();
            assert_eq!(grupos, vec!["begin".to_string(), "end".to_string()]);
        });
    }
}
