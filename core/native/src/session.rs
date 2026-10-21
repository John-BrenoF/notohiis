use std::fs;
use std::path::Path;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::runtime;

pub const SESSION_FILE: &str = ".session_config";
pub const MAX_RECENT: usize = 10;

fn ler_json(caminho: &Path) -> serde_json::Value {
    match fs::read(caminho) {
        Ok(bytes) => serde_json::from_slice(&bytes).unwrap_or(serde_json::Value::Null),
        Err(_) => serde_json::Value::Null,
    }
}

fn caminho_pref() -> std::path::PathBuf {
    runtime::path_from_root(&["ui", "preferencias", "preferecia.json"])
}

fn para_py(py: Python<'_>, valor: &serde_json::Value) -> PyResult<Py<PyAny>> {
    let json = py.import("json")?;
    json.call_method1("loads", (valor.to_string(),))
        .map(|objeto| objeto.unbind())
}

fn de_py(py: Python<'_>, objeto: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    let json = py.import("json")?;
    let texto: String = json.call_method1("dumps", (objeto,))?.extract()?;
    Ok(serde_json::from_str(&texto).unwrap_or(serde_json::Value::Null))
}

#[pyclass]
pub struct SessionManager;

#[pymethods]
impl SessionManager {
    #[classattr]
    const SESSION_FILE: &'static str = SESSION_FILE;

    #[classattr]
    const MAX_RECENT: i64 = MAX_RECENT as i64;

    #[staticmethod]
    fn save_session(project_root: Option<String>) {
        let project_root = match project_root {
            Some(raiz) if !raiz.is_empty() => raiz,
            _ => return,
        };

        let caminho = Path::new(SESSION_FILE);
        let mut data = if caminho.exists() {
            ler_json(caminho)
        } else {
            serde_json::Value::Null
        };
        if !data.is_object() {
            data = serde_json::json!({});
        }

        let mut recentes = data
            .get("recent_projects")
            .and_then(|valor| valor.as_array())
            .cloned()
            .unwrap_or_default();

        let alvo = serde_json::Value::String(project_root.clone());
        if let Some(posicao) = recentes.iter().position(|item| item == &alvo) {
            recentes.remove(posicao);
        }
        recentes.insert(0, alvo);
        recentes.truncate(MAX_RECENT);

        data["last_project_root"] = serde_json::Value::String(project_root);
        data["recent_projects"] = serde_json::Value::Array(recentes);

        if let Ok(conteudo) = serde_json::to_string(&data) {
            let _ = fs::write(caminho, conteudo);
        }
    }

    #[staticmethod]
    fn load_session() -> Option<String> {
        let caminho = Path::new(SESSION_FILE);
        if !caminho.exists() {
            return None;
        }
        let raiz = ler_json(caminho).get("last_project_root")?.as_str()?.to_string();
        if raiz.is_empty() || !Path::new(&raiz).exists() {
            return None;
        }
        Some(raiz)
    }

    #[staticmethod]
    fn get_recent_projects(py: Python<'_>) -> PyResult<Py<PyAny>> {
        let caminho = Path::new(SESSION_FILE);
        if !caminho.exists() {
            return Ok(pyo3::types::PyList::empty(py).unbind().into_any());
        }
        let data = ler_json(caminho);
        let recentes = data.get("recent_projects").cloned().unwrap_or_default();
        para_py(py, &recentes)
    }

    #[staticmethod]
    fn get_pref_path() -> String {
        runtime::os_path(&caminho_pref())
    }

    #[staticmethod]
    fn save_theme_pref(theme_name: String) {
        let mut prefs = Self::carregar_prefs();
        prefs["selected_theme"] = serde_json::Value::String(theme_name);
        Self::salvar_prefs(&prefs);
    }

    #[staticmethod]
    fn load_theme_pref() -> String {
        let prefs = Self::carregar_prefs();
        prefs
            .get("selected_theme")
            .and_then(|valor| valor.as_str())
            .unwrap_or("editor")
            .to_string()
    }

    #[staticmethod]
    fn load_preferences(py: Python<'_>) -> Py<PyAny> {
        let caminho = caminho_pref();
        let conteudo = fs::read_to_string(&caminho).unwrap_or_default();
        if conteudo.is_empty() {
            return PyDict::new(py).unbind().into_any();
        }
        let json = match py.import("json") {
            Ok(json) => json,
            Err(_) => return PyDict::new(py).unbind().into_any(),
        };
        match json.call_method1("loads", (conteudo,)) {
            Ok(objeto) if objeto.is_instance_of::<PyDict>() => objeto.unbind(),
            _ => PyDict::new(py).unbind().into_any(),
        }
    }

    #[staticmethod]
    fn save_preferences(py: Python<'_>, data: Py<PyAny>) {
        let objeto = data.bind(py);
        match de_py(py, objeto) {
            Ok(valor) if valor.is_object() => Self::salvar_prefs(&valor),
            _ => (),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (key, default = None))]
    fn get_ui_setting(py: Python<'_>, key: String, default: Option<Py<PyAny>>) -> Py<PyAny> {
        let prefs = Self::carregar_prefs();
        let vazio = serde_json::json!({});
        let ui = prefs.get("ui").unwrap_or(&vazio);
        match ui.get(&key) {
            Some(valor) => para_py(py, valor).unwrap_or_else(|_| py.None()),
            None => default.unwrap_or_else(|| py.None()),
        }
    }

    #[staticmethod]
    fn set_ui_setting(py: Python<'_>, key: String, value: Py<PyAny>) {
        let mut prefs = Self::carregar_prefs();
        if !prefs.is_object() {
            prefs = serde_json::json!({});
        }
        let valor = match de_py(py, value.bind(py)) {
            Ok(valor) => valor,
            Err(_) => return,
        };
        let mut ui = prefs
            .get("ui")
            .cloned()
            .unwrap_or_else(|| serde_json::json!({}));
        if !ui.is_object() {
            ui = serde_json::json!({});
        }
        if let Some(mapa) = ui.as_object_mut() {
            mapa.insert(key, valor);
        }
        prefs["ui"] = ui;
        Self::salvar_prefs(&prefs);
    }
}

impl SessionManager {
    fn carregar_prefs() -> serde_json::Value {
        let caminho = caminho_pref();
        if !caminho.exists() {
            return serde_json::json!({});
        }
        let data = ler_json(&caminho);
        if data.is_object() {
            data
        } else {
            serde_json::json!({})
        }
    }

    fn salvar_prefs(data: &serde_json::Value) {
        let caminho = caminho_pref();
        if let Some(pai) = caminho.parent() {
            fs::create_dir_all(pai).ok();
        }
        if let Ok(conteudo) = serde_json::to_string_pretty(data) {
            fs::write(&caminho, conteudo).ok();
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SessionManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    fn com_cwd_isolado<T>(rotulo: &str, teste: impl FnOnce() -> T) -> T {
        let _guarda = crate::teste_util::lock_global();
        let dir = crate::teste_util::dir_temporario(rotulo);
        let anterior = std::env::current_dir().unwrap();
        std::env::set_current_dir(&dir).unwrap();
        let resultado = teste();
        std::env::set_current_dir(anterior).unwrap();
        resultado
    }

    #[test]
    fn save_e_load_session_roundtrip() {
        com_cwd_isolado("sess_rt", || {
            Python::attach(|py| {
                let modulo = PyModule::new(py, "teste").unwrap();
                register(&modulo).unwrap();
                let classe = modulo.getattr("SessionManager").unwrap();
                let raiz = std::env::temp_dir().to_string_lossy().to_string();
                classe.call_method1("save_session", (raiz.clone(),)).unwrap();
                let lida: String = classe.call_method0("load_session").unwrap().extract().unwrap();
                assert_eq!(lida, raiz);
            });
        });
    }

    #[test]
    fn load_session_retorna_none_sem_arquivo() {
        com_cwd_isolado("sess_none", || {
            Python::attach(|py| {
                let modulo = PyModule::new(py, "teste").unwrap();
                register(&modulo).unwrap();
                let classe = modulo.getattr("SessionManager").unwrap();
                assert!(classe.call_method0("load_session").unwrap().is_none());
            });
        });
    }

    #[test]
    fn recent_projects_mantem_ordem_e_limita_a_10() {
        com_cwd_isolado("sess_recent", || {
            Python::attach(|py| {
                let modulo = PyModule::new(py, "teste").unwrap();
                register(&modulo).unwrap();
                let classe = modulo.getattr("SessionManager").unwrap();
                for indice in 0..15 {
                    classe
                        .call_method1("save_session", (format!("/tmp/projeto_{}", indice),))
                        .unwrap();
                }
                let recentes = classe.call_method0("get_recent_projects").unwrap();
                let recentes: Vec<String> = recentes.extract().unwrap();
                assert_eq!(recentes.len(), 10);
                assert_eq!(recentes[0], "/tmp/projeto_14");
                classe.call_method1("save_session", ("/tmp/projeto_3",)).unwrap();
                let recentes: Vec<String> = classe.call_method0("get_recent_projects").unwrap().extract().unwrap();
                assert_eq!(recentes[0], "/tmp/projeto_3");
                assert_eq!(recentes.iter().filter(|p| *p == "/tmp/projeto_3").count(), 1);
            });
        });
    }

    #[test]
    fn save_session_ignora_raiz_vazia() {
        com_cwd_isolado("sess_vazio", || {
            Python::attach(|py| {
                let modulo = PyModule::new(py, "teste").unwrap();
                register(&modulo).unwrap();
                let classe = modulo.getattr("SessionManager").unwrap();
                classe.call_method1("save_session", ("",)).unwrap();
                assert!(classe.call_method0("load_session").unwrap().is_none());
            });
        });
    }

    #[test]
    fn preferencias_de_tema_e_ui_roundtrip() {
        let _guarda = crate::teste_util::lock_global();
        let dir = crate::teste_util::dir_temporario("sess_pref");
        crate::runtime::definir_raiz(dir.to_string_lossy().to_string());

        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("SessionManager").unwrap();

            let padrao: String = classe.call_method0("load_theme_pref").unwrap().extract().unwrap();
            assert_eq!(padrao, "editor");

            classe.call_method1("save_theme_pref", ("meu_tema",)).unwrap();
            let lido: String = classe.call_method0("load_theme_pref").unwrap().extract().unwrap();
            assert_eq!(lido, "meu_tema");

            let padrao_ui: bool = classe
                .call_method1("get_ui_setting", ("sidebar_width", true))
                .unwrap()
                .extract()
                .unwrap();
            assert!(padrao_ui);
            classe.call_method1("set_ui_setting", ("sidebar_width", 250)).unwrap();
            let largura: i64 = classe
                .call_method1("get_ui_setting", ("sidebar_width", 0))
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(largura, 250);

            let prefs = classe.call_method0("load_preferences").unwrap();
            let dicionario = pyo3::types::PyDict::new(py);
            dicionario.set_item("a", 1).unwrap();
            classe.call_method1("save_preferences", (dicionario,)).unwrap();
            let prefs2 = classe.call_method0("load_preferences").unwrap();
            assert!(prefs2.get_item("a").unwrap().extract::<i64>().unwrap() == 1);
            let _ = prefs;
        });
    }
}
