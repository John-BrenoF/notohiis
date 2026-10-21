use std::sync::Mutex;

use pyo3::prelude::*;
use pyo3::types::PyBool;

use crate::events::DIRTY_CHANGED;

const SEPARADORES_LOGICOS: &[&str] = &[
    " ", "\n", "\t", ".", ",", "!", "?", ";", ":", "(", "[", "{", "=", "+", "-", "*", "/", "\\",
];

struct Estado {
    editor: Option<Py<PyAny>>,
    baseline_content: String,
    transaction_level: i64,
    chars_since_separator: i64,
    is_replaying_history: bool,
    dirty: bool,
}

#[pyclass]
pub struct EditHistoryManager {
    events: Py<PyAny>,
    estado: Mutex<Estado>,
}

impl EditHistoryManager {
    pub fn novo(events: Py<PyAny>) -> Self {
        EditHistoryManager {
            events,
            estado: Mutex::new(Estado {
                editor: None,
                baseline_content: String::new(),
                transaction_level: 0,
                chars_since_separator: 0,
                is_replaying_history: false,
                dirty: false,
            }),
        }
    }

    pub fn sujeira(&self) -> bool {
        self.estado.lock().unwrap().dirty
    }

    pub fn em_transacao(&self) -> bool {
        self.estado.lock().unwrap().transaction_level > 0
    }

    pub fn anexar_editor(&self, editor: Py<PyAny>) {
        self.estado.lock().unwrap().editor = Some(editor);
    }

    fn editor_ativo(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        let editor = {
            let estado = self.estado.lock().unwrap();
            estado.editor.as_ref().map(|editor| editor.clone_ref(py))
        }?;
        match editor.bind(py).is_truthy() {
            Ok(true) => Some(editor),
            _ => None,
        }
    }

    pub fn definir_sujeira(&self, py: Python<'_>, dirty: bool) -> PyResult<()> {
        {
            let mut estado = self.estado.lock().unwrap();
            if estado.dirty == dirty {
                return Ok(());
            }
            estado.dirty = dirty;
        }
        let sujeira = PyBool::new(py, dirty).to_owned().into_any().unbind();
        self.events
            .bind(py)
            .call_method1("emit", (DIRTY_CHANGED, sujeira))?;
        Ok(())
    }

    fn sincronizar_com_editor(&self, py: Python<'_>, editor: &Py<PyAny>) -> PyResult<()> {
        let texto: String = editor.call_method0(py, "get_text")?.extract(py)?;
        let baseline = self.estado.lock().unwrap().baseline_content.clone();
        self.definir_sujeira(py, texto != baseline)
    }

    pub fn conteudo_carregado(
        &self,
        py: Python<'_>,
        content: String,
        baseline: Option<String>,
        force_dirty: bool,
    ) -> PyResult<()> {
        if let Some(editor) = self.editor_ativo(py) {
            editor.call_method0(py, "reset_undo_stack")?;
        }

        let baseline = baseline.unwrap_or_else(|| content.clone());
        {
            let mut estado = self.estado.lock().unwrap();
            estado.baseline_content = baseline.clone();
            estado.chars_since_separator = 0;
        }

        if force_dirty {
            self.definir_sujeira(py, true)
        } else {
            self.definir_sujeira(py, content != baseline)
        }
    }

    pub fn marcar_salvo(&self, py: Python<'_>, content: String) -> PyResult<()> {
        self.estado.lock().unwrap().baseline_content = content;
        self.definir_sujeira(py, false)
    }

    pub fn entrada_texto(&self, py: Python<'_>, char: Option<String>) -> PyResult<()> {
        let (editor, replaying) = {
            let estado = self.estado.lock().unwrap();
            (estado.editor.clone(), estado.is_replaying_history)
        };
        if replaying {
            return Ok(());
        }
        let editor = match editor {
            Some(editor) if editor.bind(py).is_truthy()? => editor,
            _ => return Ok(()),
        };

        self.sincronizar_com_editor(py, &editor)?;

        let Some(char) = char else { return Ok(()) };
        if char.is_empty() {
            return Ok(());
        }

        let eh_separador = SEPARADORES_LOGICOS.iter().any(|sep| *sep == char);
        let estourou = {
            let mut estado = self.estado.lock().unwrap();
            estado.chars_since_separator += 1;
            estado.chars_since_separator >= 15
        };
        if eh_separador || estourou {
            editor.call_method0(py, "edit_separator")?;
            self.estado.lock().unwrap().chars_since_separator = 0;
        }
        Ok(())
    }

    pub fn iniciar_transacao(&self, py: Python<'_>) -> PyResult<()> {
        let (deve_chamar, editor) = {
            let mut estado = self.estado.lock().unwrap();
            let deve_chamar = estado.transaction_level == 0;
            let editor = estado.editor.clone();
            if deve_chamar && editor.is_some() {
                estado.chars_since_separator = 0;
            }
            (deve_chamar && editor.is_some(), editor)
        };
        if deve_chamar {
            if let Some(editor) = editor {
                editor.call_method0(py, "begin_undo_group")?;
            }
        }
        self.estado.lock().unwrap().transaction_level += 1;
        Ok(())
    }

    pub fn finalizar_transacao(&self, py: Python<'_>) -> PyResult<()> {
        let (no_nivel_zero, editor) = {
            let mut estado = self.estado.lock().unwrap();
            estado.transaction_level = (estado.transaction_level - 1).max(0);
            (estado.transaction_level == 0, estado.editor.clone())
        };
        if no_nivel_zero {
            if let Some(editor) = editor {
                if editor.bind(py).is_truthy()? {
                    editor.call_method0(py, "end_undo_group")?;
                    self.sincronizar_com_editor(py, &editor)?;
                }
            }
        }
        Ok(())
    }

    pub fn desfazer(&self, py: Python<'_>) -> PyResult<()> {
        self.reproduzir(py, "undo")
    }

    pub fn refazer(&self, py: Python<'_>) -> PyResult<()> {
        self.reproduzir(py, "redo")
    }

    fn reproduzir(&self, py: Python<'_>, metodo: &str) -> PyResult<()> {
        let editor = {
            let mut estado = self.estado.lock().unwrap();
            if estado.is_replaying_history {
                return Ok(());
            }
            let editor = match estado.editor.clone() {
                Some(editor) => editor,
                None => return Ok(()),
            };
            if !editor.bind(py).is_truthy()? {
                return Ok(());
            }
            estado.is_replaying_history = true;
            editor
        };

        let resultado = editor.call_method0(py, metodo);

        {
            let mut estado = self.estado.lock().unwrap();
            estado.is_replaying_history = false;
        }

        resultado?;

        self.estado.lock().unwrap().chars_since_separator = 0;
        self.sincronizar_com_editor(py, &editor)
    }
}

#[pymethods]
impl EditHistoryManager {
    #[new]
    fn new(event_bus: Py<PyAny>) -> Self {
        Self::novo(event_bus)
    }

    #[getter]
    fn is_dirty(&self) -> bool {
        self.sujeira()
    }

    #[getter]
    fn is_in_transaction(&self) -> bool {
        self.em_transacao()
    }

    fn attach_editor(&self, editor: Py<PyAny>) {
        self.anexar_editor(editor);
    }

    #[pyo3(signature = (content, baseline = None, force_dirty = false))]
    fn on_content_loaded(
        &self,
        py: Python<'_>,
        content: String,
        baseline: Option<String>,
        force_dirty: bool,
    ) -> PyResult<()> {
        self.conteudo_carregado(py, content, baseline, force_dirty)
    }

    fn mark_saved(&self, py: Python<'_>, content: String) -> PyResult<()> {
        self.marcar_salvo(py, content)
    }

    fn set_dirty(&self, py: Python<'_>, dirty: bool) -> PyResult<()> {
        self.definir_sujeira(py, dirty)
    }

    fn sync_dirty(&self, py: Python<'_>) -> PyResult<()> {
        match self.editor_ativo(py) {
            Some(editor) => self.sincronizar_com_editor(py, &editor),
            None => Ok(()),
        }
    }

    fn on_text_input(&self, py: Python<'_>, char: Option<String>) -> PyResult<()> {
        self.entrada_texto(py, char)
    }

    fn begin_transaction(&self, py: Python<'_>) -> PyResult<()> {
        self.iniciar_transacao(py)
    }

    fn end_transaction(&self, py: Python<'_>) -> PyResult<()> {
        self.finalizar_transacao(py)
    }

    fn perform_undo(&self, py: Python<'_>) -> PyResult<()> {
        self.desfazer(py)
    }

    fn perform_redo(&self, py: Python<'_>) -> PyResult<()> {
        self.refazer(py)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EditHistoryManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;
    use crate::events::EventBus;
    use crate::teste_util::editor_falso;

    fn historico_com_editor(py: Python<'_>, texto: &str) -> (Py<EventBus>, Py<EditHistoryManager>, Py<PyAny>) {
        let bus = Py::new(py, EventBus::novo()).unwrap();
        let manager =
            Py::new(py, EditHistoryManager::novo(bus.clone_ref(py).into_any())).unwrap();
        let editor = editor_falso(py, texto);
        manager.borrow(py).anexar_editor(editor.clone_ref(py));
        (bus, manager, editor)
    }

    #[test]
    fn conteudo_identico_a_baseline_nao_fica_sujejo() {
        Python::attach(|py| {
            let (_bus, manager, _editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, false)
                .unwrap();
            assert!(!manager.borrow(py).sujeira());
        });
    }

    #[test]
    fn conteudo_diferente_da_baseline_fica_sujejo() {
        Python::attach(|py| {
            let (_bus, manager, _editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "xyz".to_string(), Some("abc".to_string()), false)
                .unwrap();
            assert!(manager.borrow(py).sujeira());
        });
    }

    #[test]
    fn baseline_padrao_e_o_proprio_conteudo() {
        Python::attach(|py| {
            let (_bus, manager, _editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "xyz".to_string(), None, false)
                .unwrap();
            assert!(!manager.borrow(py).sujeira());
        });
    }

    #[test]
    fn force_dirty_mesmo_com_conteudo_igual() {
        Python::attach(|py| {
            let (_bus, manager, _editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, true)
                .unwrap();
            assert!(manager.borrow(py).sujeira());
        });
    }

    #[test]
    fn carregar_conteudo_zera_pilha_do_editor() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, false)
                .unwrap();
            let resets: i64 = editor.getattr(py, "resets").unwrap().extract(py).unwrap();
            assert_eq!(resets, 1);
        });
    }

    #[test]
    fn mark_saved_limpa_sujeira_e_atualiza_baseline() {
        Python::attach(|py| {
            let (_bus, manager, _editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, false)
                .unwrap();
            manager.borrow(py).definir_sujeira(py, true).unwrap();
            assert!(manager.borrow(py).sujeira());
            manager
                .borrow(py)
                .marcar_salvo(py, "novo".to_string())
                .unwrap();
            assert!(!manager.borrow(py).sujeira());
        });
    }

    #[test]
    fn entrada_de_texto_cria_separador_apos_limite() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "");
            manager
                .borrow(py)
                .conteudo_carregado(py, "".to_string(), None, false)
                .unwrap();

            for _ in 0..14 {
                manager
                    .borrow(py)
                    .entrada_texto(py, Some("a".to_string()))
                    .unwrap();
            }
            let separadores: i64 = editor.getattr(py, "separadores").unwrap().extract(py).unwrap();
            assert_eq!(separadores, 0);

            manager
                .borrow(py)
                .entrada_texto(py, Some("a".to_string()))
                .unwrap();
            let separadores: i64 = editor.getattr(py, "separadores").unwrap().extract(py).unwrap();
            assert_eq!(separadores, 1);
        });
    }

    #[test]
    fn separador_logico_gera_ponto_de_undo_imediatamente() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "");
            manager
                .borrow(py)
                .conteudo_carregado(py, "".to_string(), None, false)
                .unwrap();
            for caractere in ["o", "i", " "] {
                manager
                    .borrow(py)
                    .entrada_texto(py, Some(caractere.to_string()))
                    .unwrap();
            }
            let separadores: i64 = editor.getattr(py, "separadores").unwrap().extract(py).unwrap();
            assert_eq!(separadores, 1);
        });
    }

    #[test]
    fn transacoes_abrem_e_fecham_grupos_de_undo() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "");
            manager.borrow(py).iniciar_transacao(py).unwrap();
            assert!(manager.borrow(py).em_transacao());
            manager.borrow(py).iniciar_transacao(py).unwrap();
            manager.borrow(py).finalizar_transacao(py).unwrap();
            assert!(manager.borrow(py).em_transacao());
            manager.borrow(py).finalizar_transacao(py).unwrap();
            assert!(!manager.borrow(py).em_transacao());

            let grupos = editor.getattr(py, "grupos").unwrap();
            let grupos: Vec<String> = grupos.extract(py).unwrap();
            assert_eq!(grupos, vec!["begin".to_string(), "end".to_string()]);
        });
    }

    #[test]
    fn undo_e_redo_disparam_editor_e_recalculam_sujeira() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, false)
                .unwrap();

            manager.borrow(py).desfazer(py).unwrap();
            let undos: i64 = editor.getattr(py, "undos").unwrap().extract(py).unwrap();
            assert_eq!(undos, 1);
            assert!(manager.borrow(py).sujeira());

            manager.borrow(py).refazer(py).unwrap();
            let redos: i64 = editor.getattr(py, "redos").unwrap().extract(py).unwrap();
            assert_eq!(redos, 1);
        });
    }

    #[test]
    fn entrada_de_texto_e_inofensiva_durante_replay() {
        Python::attach(|py| {
            let (_bus, manager, editor) = historico_com_editor(py, "abc");
            manager
                .borrow(py)
                .conteudo_carregado(py, "abc".to_string(), None, false)
                .unwrap();
            {
                let referencia = manager.borrow(py);
                referencia.estado.lock().unwrap().is_replaying_history = true;
            }
            manager
                .borrow(py)
                .entrada_texto(py, Some("z".to_string()))
                .unwrap();
            let separadores: i64 = editor.getattr(py, "separadores").unwrap().extract(py).unwrap();
            assert_eq!(separadores, 0);
            {
                let referencia = manager.borrow(py);
                referencia.estado.lock().unwrap().is_replaying_history = false;
            }
        });
    }

    #[test]
    fn api_python_expoe_getters_e_metodos() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            crate::events::register(&modulo).unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("EditHistoryManager").unwrap();
            let bus_classe = modulo.getattr("EventBus").unwrap().call0().unwrap();
            let manager = classe.call1((bus_classe,)).unwrap();
            assert_eq!(manager.getattr("is_dirty").unwrap().extract::<bool>().unwrap(), false);
            assert_eq!(manager.getattr("is_in_transaction").unwrap().extract::<bool>().unwrap(), false);
            manager.call_method1("set_dirty", (true,)).unwrap();
            assert_eq!(manager.getattr("is_dirty").unwrap().extract::<bool>().unwrap(), true);
            manager.call_method1("mark_saved", ("x",)).unwrap();
            assert_eq!(manager.getattr("is_dirty").unwrap().extract::<bool>().unwrap(), false);
        });
    }

    #[test]
    fn aceita_event_bus_de_python_para_sujeira() {
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "vistos = []\n\
                 class BusPython:\n\
                 \x20   def emit(self, event_name, data=None): vistos.append((event_name, data))\n\
                 bus = BusPython()\n",
            );
            let escopo = escopo.bind(py);
            let bus = escopo.get_item("bus").unwrap().unwrap();

            let manager = EditHistoryManager::novo(bus.unbind());
            manager.definir_sujeira(py, true).unwrap();
            manager.definir_sujeira(py, true).unwrap(); // sem reemitir
            manager.definir_sujeira(py, false).unwrap();

            let vistos = escopo.get_item("vistos").unwrap().unwrap();
            let vistos: Vec<(String, bool)> = vistos.extract().unwrap();
            assert_eq!(
                vistos,
                vec![
                    (DIRTY_CHANGED.to_string(), true),
                    (DIRTY_CHANGED.to_string(), false),
                ]
            );
        });
    }
}
