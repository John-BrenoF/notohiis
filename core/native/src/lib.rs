mod app_context;
mod autocomplete;
mod buffer;
mod constants;
mod edit_history;
mod events;
mod file_manager;
mod file_name_search;
mod interfaces;
mod lsp_client;
mod runtime;
mod session;
mod tab_manager;
mod theme_manager;

use pyo3::prelude::*;

#[pyfunction]
pub fn set_project_root(path: String) {
    runtime::definir_raiz(path);
}

#[pyfunction]
pub fn get_project_root() -> String {
    runtime::os_path(&runtime::project_root())
}

#[pyfunction]
pub fn is_native_core() -> bool {
    true
}

#[pymodule]
fn notohiis_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    constants::register(&m)?;
    events::register(&m)?;
    interfaces::register(&m)?;
    buffer::register(&m)?;
    file_manager::register(&m)?;
    file_name_search::register(&m)?;
    session::register(&m)?;
    theme_manager::register(&m)?;
    tab_manager::register(&m)?;
    edit_history::register(&m)?;
    lsp_client::register(&m)?;
    autocomplete::register(&m)?;
    app_context::register(&m)?;

    m.add_function(wrap_pyfunction!(set_project_root, m)?)?;
    m.add_function(wrap_pyfunction!(get_project_root, m)?)?;
    m.add_function(wrap_pyfunction!(is_native_core, m)?)?;
    Ok(())
}

#[cfg(test)]
pub(crate) mod teste_util {
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::{Mutex, MutexGuard, OnceLock};

    static LOCK_GLOBAL: OnceLock<Mutex<()>> = OnceLock::new();
    static CONTADOR: AtomicU32 = AtomicU32::new(0);

    pub fn lock_global() -> MutexGuard<'static, ()> {
        LOCK_GLOBAL
            .get_or_init(|| Mutex::new(()))
            .lock()
            .unwrap_or_else(|poisonado| poisonado.into_inner())
    }

    pub fn dir_temporario(rotulo: &str) -> PathBuf {
        let id = CONTADOR.fetch_add(1, Ordering::SeqCst);
        let caminho = std::env::temp_dir().join(format!(
            "notohiis_teste_{}_{}_{}",
            rotulo,
            std::process::id(),
            id
        ));
        let _ = std::fs::remove_dir_all(&caminho);
        std::fs::create_dir_all(&caminho).expect("criar diretório temporário");
        caminho
    }

    pub fn rodar(py: pyo3::Python<'_>, codigo: &str) -> pyo3::Py<pyo3::types::PyDict> {
        use pyo3::types::PyDict;
        let globals = PyDict::new(py);
        let codigo = std::ffi::CString::new(codigo).expect("código sem NUL interno");
        py.run(&codigo, Some(&globals), None).expect("executar código de teste");
        globals.unbind()
    }

    pub fn editor_falso(py: pyo3::Python<'_>, texto_inicial: &str) -> pyo3::Py<pyo3::PyAny> {
        let globals = pyo3::types::PyDict::new(py);
        let codigo = format!(
            "class EditorFake:\n\
             \x20   def __init__(self, texto):\n\
             \x20       self.text = texto\n\
             \x20       self.separadores = 0\n\
             \x20       self.grupos = []\n\
             \x20       self.resets = 0\n\
             \x20       self.undos = 0\n\
             \x20       self.redos = 0\n\
             \x20   def get_text(self): return self.text\n\
             \x20   def reset_undo_stack(self): self.resets += 1\n\
             \x20   def edit_separator(self): self.separadores += 1\n\
             \x20   def begin_undo_group(self): self.grupos.append('begin')\n\
             \x20   def end_undo_group(self): self.grupos.append('end')\n\
             \x20   def undo(self): self.undos += 1; self.text = ''\n\
             \x20   def redo(self): self.redos += 1; self.text = 'refeito'\n\n\
             editor = EditorFake({texto:?})\n",
            texto = texto_inicial
        );
        let codigo = std::ffi::CString::new(codigo).expect("código sem NUL");
        py.run(&codigo, Some(&globals), None).expect("criar editor falso");
        use pyo3::types::PyDictMethods as _;
        globals.get_item("editor").unwrap().unwrap().unbind()
    }
}
