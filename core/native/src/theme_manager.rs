use std::fs;
use std::path::PathBuf;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::runtime;

pub fn tema_dir() -> PathBuf {
    runtime::path_from_root(&["ui", "estilo"])
}

fn listar_temas() -> Vec<String> {
    let diretorio = tema_dir();
    if !diretorio.is_dir() {
        return Vec::new();
    }
    let mut temas: Vec<String> = match fs::read_dir(&diretorio) {
        Ok(leitura) => leitura
            .flatten()
            .map(|entrada| entrada.file_name().to_string_lossy().into_owned())
            .filter(|nome| nome.to_lowercase().ends_with(".json"))
            .collect(),
        Err(_) => return Vec::new(),
    };
    temas.sort();
    temas
}

#[pyclass]
pub struct ThemeManager;

#[pymethods]
impl ThemeManager {
    #[staticmethod]
    fn get_theme_dir() -> String {
        runtime::os_path(&tema_dir())
    }

    #[staticmethod]
    fn list_themes(py: Python<'_>) -> PyResult<Py<PyAny>> {
        Ok(PyList::new(py, listar_temas())?.unbind().into_any())
    }

    #[staticmethod]
    #[pyo3(signature = (theme_name = None))]
    fn resolve_theme_path(theme_name: Option<String>) -> String {
        let diretorio = tema_dir();
        let tema = match theme_name {
            Some(nome) if !nome.is_empty() => {
                if nome.to_lowercase().ends_with(".json") {
                    nome
                } else {
                    format!("{}.json", nome)
                }
            }
            _ => "editor.json".to_string(),
        };
        runtime::os_path(&diretorio.join(tema))
    }

    #[staticmethod]
    #[pyo3(signature = (theme_name = None))]
    fn load_theme(py: Python<'_>, theme_name: Option<String>) -> Py<PyAny> {
        let mut caminho = PathBuf::from(Self::resolve_theme_path(theme_name));

        if !caminho.exists() {
            let temas = listar_temas();
            match temas.first() {
                Some(primeiro) => caminho = tema_dir().join(primeiro),
                None => return PyDict::new(py).unbind().into_any(),
            }
        }

        let conteudo = fs::read_to_string(&caminho).unwrap_or_default();
        match runtime::py_json_loads(py, conteudo) {
            Ok(objeto) if objeto.bind(py).is_instance_of::<PyDict>() => objeto,
            _ => PyDict::new(py).unbind().into_any(),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (theme_name = None))]
    fn get_theme_name(theme_name: Option<String>) -> String {
        match theme_name {
            Some(nome) if !nome.is_empty() => {
                let base = runtime::basename(&nome);
                match std::path::Path::new(&base).file_stem() {
                    Some(stem) => stem.to_string_lossy().into_owned(),
                    None => String::new(),
                }
            }
            _ => "editor".to_string(),
        }
    }

    #[staticmethod]
    fn get_theme_display_list(py: Python<'_>) -> PyResult<Py<PyAny>> {
        let nomes: Vec<String> = listar_temas()
            .iter()
            .map(|nome| {
                match std::path::Path::new(nome).file_stem() {
                    Some(stem) => stem.to_string_lossy().into_owned(),
                    None => String::new(),
                }
            })
            .collect();
        Ok(PyList::new(py, nomes)?.unbind().into_any())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ThemeManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;
    use crate::teste_util::lock_global;

    fn raiz_com_temas() -> std::path::PathBuf {
        let dir = crate::teste_util::dir_temporario("temas");
        let estilo = dir.join("ui").join("estilo");
        fs::create_dir_all(&estilo).unwrap();
        fs::write(estilo.join("editor.json"), "{\"nome\": \"Editor\", \"bg\": \"#111\"}").unwrap();
        fs::write(estilo.join("claro.json"), "{\"nome\": \"Claro\", \"bg\": \"#fff\"}").unwrap();
        fs::write(estilo.join("nao_e_tema.txt"), "ignorar").unwrap();
        crate::runtime::definir_raiz(dir.to_string_lossy().to_string());
        dir
    }

    #[test]
    fn list_themes_inclui_apenas_json_ordenados() {
        let _guarda = lock_global();
        let _dir = raiz_com_temas();
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("ThemeManager").unwrap();
            let lista = classe.call_method0("list_themes").unwrap();
            let temas: Vec<String> = lista.extract().unwrap();
            assert_eq!(temas, vec!["claro.json".to_string(), "editor.json".to_string()]);
        });
    }

    #[test]
    fn resolve_theme_path_adiciona_extensao() {
        let _guarda = lock_global();
        let _dir = raiz_com_temas();
        let caminho = ThemeManager::resolve_theme_path(Some("claro".to_string()));
        assert!(caminho.ends_with("ui/estilo/claro.json"));
        let padrao = ThemeManager::resolve_theme_path(None);
        assert!(padrao.ends_with("ui/estilo/editor.json"));
        let ja_com_extensao = ThemeManager::resolve_theme_path(Some("claro.json".to_string()));
        assert!(ja_com_extensao.ends_with("claro.json"));
    }

    #[test]
    fn load_theme_devolve_dicionario_do_arquivo() {
        let _guarda = lock_global();
        let _dir = raiz_com_temas();
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("ThemeManager").unwrap();
            let tema = classe.call_method1("load_theme", ("claro",)).unwrap();
            assert_eq!(tema.get_item("bg").unwrap().extract::<String>().unwrap(), "#fff");
        });
    }

    #[test]
    fn load_theme_inexistente_cai_no_primeiro_tema() {
        let _guarda = lock_global();
        let _dir = raiz_com_temas();
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("ThemeManager").unwrap();
            let tema = classe.call_method1("load_theme", ("nao_existe",)).unwrap();
            assert_eq!(tema.get_item("bg").unwrap().extract::<String>().unwrap(), "#fff");
        });
    }

    #[test]
    fn load_theme_sem_nenhum_tema_retorna_dict_vazio() {
        let _guarda = lock_global();
        let dir = crate::teste_util::dir_temporario("temas_vazio");
        crate::runtime::definir_raiz(dir.to_string_lossy().to_string());
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("ThemeManager").unwrap();
            let tema = classe.call_method0("load_theme").unwrap();
            assert!(tema.is_empty().unwrap());
            let lista = classe.call_method0("list_themes").unwrap();
            assert_eq!(lista.extract::<Vec<String>>().unwrap().len(), 0);
        });
    }

    #[test]
    fn get_theme_name_normaliza_caminho_e_extensao() {
        assert_eq!(ThemeManager::get_theme_name(None), "editor");
        assert_eq!(ThemeManager::get_theme_name(Some("".to_string())), "editor");
        assert_eq!(ThemeManager::get_theme_name(Some("/x/y/azul.json".to_string())), "azul");
        assert_eq!(ThemeManager::get_theme_name(Some("azul".to_string())), "azul");
    }

    #[test]
    fn display_list_sem_extensao() {
        let _guarda = lock_global();
        let _dir = raiz_com_temas();
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("ThemeManager").unwrap();
            let lista = classe.call_method0("get_theme_display_list").unwrap();
            let nomes: Vec<String> = lista.extract().unwrap();
            assert_eq!(nomes, vec!["claro".to_string(), "editor".to_string()]);
        });
    }
}
