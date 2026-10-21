use std::sync::Mutex;

use pyo3::prelude::*;

use crate::buffer;
use crate::runtime;

#[pyclass]
pub struct Tab {
    #[pyo3(get)]
    pub id: i64,
    #[pyo3(get, set)]
    pub path: Option<String>,
    #[pyo3(get, set)]
    pub content: String,
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub is_dirty: bool,
}

#[pymethods]
impl Tab {
    #[new]
    #[pyo3(signature = (id, path = None, content = String::new(), title = String::from("Novo Arquivo"), is_dirty = false))]
    fn new(id: i64, path: Option<String>, content: String, title: String, is_dirty: bool) -> Self {
        Tab { id, path, content, title, is_dirty }
    }

    #[getter]
    fn display_name(&self) -> String {
        match &self.path {
            Some(caminho) if !caminho.is_empty() => {
                let base = runtime::basename(caminho);
                if base.is_empty() {
                    self.title.clone()
                } else {
                    base
                }
            }
            _ => self.title.clone(),
        }
    }
}

struct Estado {
    tabs: Vec<Py<Tab>>,
    next_id: i64,
    active_tab_id: Option<i64>,
}

#[pyclass]
pub struct TabManager {
    estado: Mutex<Estado>,
}

impl TabManager {
    pub fn novo() -> Self {
        TabManager {
            estado: Mutex::new(Estado { tabs: Vec::new(), next_id: 1, active_tab_id: None }),
        }
    }

    fn achar_por_id(&self, py: Python<'_>, tab_id: Option<i64>) -> Option<Py<Tab>> {
        let estado = self.estado.lock().unwrap();
        let alvo = tab_id?;
        estado
            .tabs
            .iter()
            .find(|tab| tab.bind(py).borrow().id == alvo)
            .cloned()
    }
}

#[pymethods]
impl TabManager {
    #[new]
    fn new() -> Self {
        Self::novo()
    }

    #[getter(tabs)]
    fn obter_tabs(&self) -> Vec<Py<Tab>> {
        self.estado.lock().unwrap().tabs.clone()
    }

    #[setter]
    fn set_tabs(&self, tabs: Vec<Py<Tab>>) {
        self.estado.lock().unwrap().tabs = tabs;
    }

    #[getter]
    fn active_tab_id(&self) -> Option<i64> {
        self.estado.lock().unwrap().active_tab_id
    }

    #[setter]
    fn set_active_tab_id(&self, tab_id: Option<i64>) {
        self.estado.lock().unwrap().active_tab_id = tab_id;
    }

    #[pyo3(signature = (path = None, content = None, set_active = true))]
    fn create_tab(
        &self,
        py: Python<'_>,
        path: Option<String>,
        content: Option<String>,
        set_active: bool,
    ) -> PyResult<Py<Tab>> {
        let tem_caminho = path.as_deref().map(|p| !p.is_empty()).unwrap_or(false);
        let conteudo = match content {
            Some(conteudo) => conteudo,
            None => match &path {
                Some(caminho) if tem_caminho => buffer::ler_arquivo(caminho),
                _ => String::new(),
            },
        };

        let titulo = match &path {
            Some(caminho) if tem_caminho => {
                let base = runtime::basename(caminho);
                if base.is_empty() { "Novo Arquivo".to_string() } else { base }
            }
            _ => "Novo Arquivo".to_string(),
        };

        let mut estado = self.estado.lock().unwrap();
        let tab_id = estado.next_id;
        estado.next_id += 1;
        let tab = Py::new(
            py,
            Tab { id: tab_id, path, content: conteudo, title: titulo, is_dirty: false },
        )?;
        estado.tabs.push(tab.clone_ref(py));
        drop(estado);

        if set_active {
            self.select_tab(py, tab_id);
        }
        Ok(tab)
    }

    fn open_file(&self, py: Python<'_>, path: String) -> PyResult<Py<Tab>> {
        let existente = {
            let estado = self.estado.lock().unwrap();
            estado
                .tabs
                .iter()
                .find(|tab| tab.bind(py).borrow().path.as_deref() == Some(path.as_str()))
                .cloned()
        };
        match existente {
            Some(tab) => {
                let tab_id = tab.bind(py).borrow().id;
                self.select_tab(py, tab_id);
                Ok(tab)
            }
            None => self.create_tab(py, Some(path), None, true),
        }
    }

    fn find_tab_by_path(&self, py: Python<'_>, path: String) -> Option<Py<Tab>> {
        let estado = self.estado.lock().unwrap();
        estado
            .tabs
            .iter()
            .find(|tab| tab.bind(py).borrow().path.as_deref() == Some(path.as_str()))
            .cloned()
    }

    fn get_active_tab(&self, py: Python<'_>) -> Option<Py<Tab>> {
        let ativo = self.estado.lock().unwrap().active_tab_id;
        self.achar_por_id(py, ativo)
    }

    fn select_tab(&self, py: Python<'_>, tab_id: i64) -> Option<Py<Tab>> {
        let ativo = self.estado.lock().unwrap().active_tab_id;
        if ativo == Some(tab_id) {
            return self.get_active_tab(py);
        }
        let existe = {
            let estado = self.estado.lock().unwrap();
            estado
                .tabs
                .iter()
                .any(|tab| tab.bind(py).borrow().id == tab_id)
        };
        if existe {
            self.estado.lock().unwrap().active_tab_id = Some(tab_id);
            return self.get_active_tab(py);
        }
        None
    }

    fn update_active_content(&self, py: Python<'_>, content: String) {
        let Some(tab) = self.get_active_tab(py) else { return };
        let mut referencia = tab.bind(py).borrow_mut();
        if referencia.content != content {
            referencia.content = content;
            referencia.is_dirty = true;
        }
    }

    fn mark_active_saved(&self, py: Python<'_>) {
        if let Some(tab) = self.get_active_tab(py) {
            tab.bind(py).borrow_mut().is_dirty = false;
        }
    }

    fn save_active_tab(&self, py: Python<'_>) -> bool {
        let Some(tab) = self.get_active_tab(py) else { return false };
        let (caminho, conteudo) = {
            let referencia = tab.bind(py).borrow();
            match &referencia.path {
                Some(caminho) if !caminho.is_empty() => {
                    (caminho.clone(), referencia.content.clone())
                }
                _ => return false,
            }
        };
        if buffer::salvar_arquivo(&caminho, &conteudo) {
            tab.bind(py).borrow_mut().is_dirty = false;
            return true;
        }
        false
    }

    fn update_tab_path(&self, py: Python<'_>, tab_id: i64, new_path: String) {
        let alvo = {
            let estado = self.estado.lock().unwrap();
            estado
                .tabs
                .iter()
                .find(|tab| tab.bind(py).borrow().id == tab_id)
                .cloned()
        };
        let Some(tab) = alvo else { return };
        let base = runtime::basename(&new_path);
        let mut referencia = tab.bind(py).borrow_mut();
        referencia.path = Some(new_path);
        if !base.is_empty() {
            referencia.title = base;
        }
    }

    #[pyo3(signature = (tab_id, force = false))]
    fn close_tab(&self, py: Python<'_>, tab_id: i64, force: bool) -> bool {
        let mut estado = self.estado.lock().unwrap();
        let alvo = estado
            .tabs
            .iter()
            .find(|tab| tab.bind(py).borrow().id == tab_id)
            .cloned();

        let Some(alvo) = alvo else { return true };

        if alvo.bind(py).borrow().is_dirty && !force {
            return false;
        }

        estado.tabs.retain(|tab| tab.bind(py).borrow().id != tab_id);
        if estado.active_tab_id == Some(tab_id) {
            estado.active_tab_id = estado
                .tabs
                .last()
                .map(|tab| tab.bind(py).borrow().id);
        }
        true
    }

    fn get_tabs(&self) -> Vec<Py<Tab>> {
        self.estado.lock().unwrap().tabs.clone()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Tab>()?;
    m.add_class::<TabManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;
    use std::fs;

    #[test]
    fn create_tab_sem_caminho_usa_titulo_padrao() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m.borrow(py).create_tab(py, None, None, true).unwrap();
            let tab = tab.bind(py);
            assert_eq!(tab.getattr("title").unwrap().extract::<String>().unwrap(), "Novo Arquivo");
            assert_eq!(tab.getattr("display_name").unwrap().extract::<String>().unwrap(), "Novo Arquivo");
            assert!(tab.getattr("path").unwrap().is_none());
            assert_eq!(tab.getattr("id").unwrap().extract::<i64>().unwrap(), 1);
            assert_eq!(m.borrow(py).get_active_tab(py).unwrap().bind(py).getattr("id").unwrap().extract::<i64>().unwrap(), 1);
        });
    }

    #[test]
    fn create_tab_com_caminho_le_arquivo_e_titulo() {
        Python::attach(|py| {
            let dir = crate::teste_util::dir_temporario("tab_arq");
            let caminho = dir.join("nota.md");
            fs::write(&caminho, "# conteúdo").unwrap();
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m
                .borrow(py)
                .create_tab(py, Some(caminho.to_string_lossy().to_string()), None, true)
                .unwrap();
            let tab = tab.bind(py);
            assert_eq!(tab.getattr("content").unwrap().extract::<String>().unwrap(), "# conteúdo");
            assert_eq!(tab.getattr("title").unwrap().extract::<String>().unwrap(), "nota.md");
            assert_eq!(tab.getattr("display_name").unwrap().extract::<String>().unwrap(), "nota.md");
            assert!(!tab.getattr("is_dirty").unwrap().extract::<bool>().unwrap());
        });
    }

    #[test]
    fn create_tab_com_conteudo_explícito_nao_lê_arquivo() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m
                .borrow(py)
                .create_tab(py, Some("/nao/existe.py".to_string()), Some("print()".to_string()), true)
                .unwrap();
            assert_eq!(tab.bind(py).getattr("content").unwrap().extract::<String>().unwrap(), "print()");
        });
    }

    #[test]
    fn open_file_reutiliza_aba_existente() {
        Python::attach(|py| {
            let dir = crate::teste_util::dir_temporario("tab_open");
            let caminho = dir.join("a.txt");
            fs::write(&caminho, "1").unwrap();
            let caminho = caminho.to_string_lossy().to_string();
            let m = Py::new(py, TabManager::novo()).unwrap();
            let primeira = m.borrow(py).open_file(py, caminho.clone()).unwrap();
            let segunda = m.borrow(py).open_file(py, caminho).unwrap();
            assert_eq!(
                primeira.bind(py).getattr("id").unwrap().extract::<i64>().unwrap(),
                segunda.bind(py).getattr("id").unwrap().extract::<i64>().unwrap()
            );
            assert_eq!(m.borrow(py).get_tabs().len(), 1);
        });
    }

    #[test]
    fn update_active_content_marca_como_sujejo() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m.borrow(py).create_tab(py, None, Some("inicial".to_string()), true).unwrap();
            m.borrow(py).update_active_content(py, "alterado".to_string());
            assert!(tab.bind(py).getattr("is_dirty").unwrap().extract::<bool>().unwrap());
            m.borrow(py).update_active_content(py, "alterado".to_string());
            assert!(tab.bind(py).getattr("is_dirty").unwrap().extract::<bool>().unwrap());
            m.borrow(py).mark_active_saved(py);
            assert!(!tab.bind(py).getattr("is_dirty").unwrap().extract::<bool>().unwrap());
        });
    }

    #[test]
    fn save_active_tab_grava_em_disco() {
        Python::attach(|py| {
            let dir = crate::teste_util::dir_temporario("tab_save");
            let caminho = dir.join("b.txt");
            let caminho = caminho.to_string_lossy().to_string();
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m.borrow(py).open_file(py, caminho.clone()).unwrap();
            m.borrow(py).update_active_content(py, "novo texto".to_string());
            assert!(m.borrow(py).save_active_tab(py));
            assert_eq!(fs::read_to_string(&caminho).unwrap(), "novo texto");
            assert!(!tab.bind(py).getattr("is_dirty").unwrap().extract::<bool>().unwrap());
        });
    }

    #[test]
    fn save_active_tab_sem_caminho_retorna_falso() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            m.borrow(py).create_tab(py, None, None, true).unwrap();
            assert!(!m.borrow(py).save_active_tab(py));
        });
    }

    #[test]
    fn close_tab_protege_aba_sujeja_sem_force() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m.borrow(py).create_tab(py, None, None, true).unwrap();
            let id = tab.bind(py).getattr("id").unwrap().extract::<i64>().unwrap();
            m.borrow(py).update_active_content(py, "mexido".to_string());
            assert!(!m.borrow(py).close_tab(py, id, false));
            assert!(m.borrow(py).close_tab(py, id, true));
            assert!(m.borrow(py).get_active_tab(py).is_none());
        });
    }

    #[test]
    fn close_tab_move_aba_ativa_para_a_anterior() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let a = m.borrow(py).create_tab(py, None, Some("1".to_string()), true).unwrap();
            let b = m.borrow(py).create_tab(py, None, Some("2".to_string()), true).unwrap();
            let id_a = a.bind(py).getattr("id").unwrap().extract::<i64>().unwrap();
            let id_b = b.bind(py).getattr("id").unwrap().extract::<i64>().unwrap();
            assert_eq!(m.borrow(py).active_tab_id(), Some(id_b));
            assert!(m.borrow(py).close_tab(py, id_b, true));
            assert_eq!(m.borrow(py).active_tab_id(), Some(id_a));
        });
    }

    #[test]
    fn close_tab_inexistente_retorna_true() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            assert!(m.borrow(py).close_tab(py, 999, false));
        });
    }

    #[test]
    fn update_tab_path_atualiza_titulo_e_display_name() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let tab = m.borrow(py).create_tab(py, None, None, true).unwrap();
            let id = tab.bind(py).getattr("id").unwrap().extract::<i64>().unwrap();
            m.borrow(py).update_tab_path(py, id, "/x/y/novo.py".to_string());
            let tab = tab.bind(py);
            assert_eq!(tab.getattr("title").unwrap().extract::<String>().unwrap(), "novo.py");
            assert_eq!(tab.getattr("display_name").unwrap().extract::<String>().unwrap(), "novo.py");
        });
    }

    #[test]
    fn select_tab_com_id_inexistente_retorna_none() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            assert!(m.borrow(py).select_tab(py, 1234).is_none());
        });
    }

    #[test]
    fn ids_sao_sequenciais_e_get_tabs_devolve_copia() {
        Python::attach(|py| {
            let m = Py::new(py, TabManager::novo()).unwrap();
            let a = m.borrow(py).create_tab(py, None, None, false).unwrap();
            let b = m.borrow(py).create_tab(py, None, None, false).unwrap();
            assert_eq!(a.bind(py).getattr("id").unwrap().extract::<i64>().unwrap(), 1);
            assert_eq!(b.bind(py).getattr("id").unwrap().extract::<i64>().unwrap(), 2);
            let copia = m.borrow(py).get_tabs();
            assert_eq!(copia.len(), 2);
        });
    }
}
