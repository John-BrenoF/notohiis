use std::path::PathBuf;
use std::sync::RwLock;

use pyo3::prelude::*;

static PROJECT_ROOT: RwLock<Option<PathBuf>> = RwLock::new(None);

pub fn definir_raiz(path: String) {
    *PROJECT_ROOT.write().unwrap() = Some(PathBuf::from(path));
}

pub fn project_root() -> PathBuf {
    PROJECT_ROOT
        .read()
        .unwrap()
        .clone()
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

pub fn path_from_root(parts: &[&str]) -> PathBuf {
    let mut path = project_root();
    for part in parts {
        path.push(part);
    }
    path
}

pub fn os_path(path: &std::path::Path) -> String {
    path.to_string_lossy().into_owned()
}

pub fn basename(path: &str) -> String {
    match path.rfind('/') {
        Some(indice) => path[indice + 1..].to_string(),
        None => path.to_string(),
    }
}

pub fn extension_of(path: &str) -> String {
    match std::path::Path::new(path).extension() {
        Some(ext) => format!(".{}", ext.to_string_lossy().to_lowercase()),
        None => String::new(),
    }
}

pub fn py_json_loads(py: Python<'_>, texto: String) -> PyResult<Py<PyAny>> {
    py.import("json")?
        .call_method1("loads", (texto,))
        .map(|objeto| objeto.unbind())
}

pub fn casefold(texto: &str) -> String {
    let mut saida = String::with_capacity(texto.len());
    for caractere in texto.chars() {
        match caractere {
            'ß' | 'ẞ' => saida.push_str("ss"),
            'ﬁ' => saida.push_str("fi"),
            'ﬂ' => saida.push_str("fl"),
            'ﬃ' => saida.push_str("ffi"),
            'ﬄ' => saida.push_str("ffl"),
            'ſ' => saida.push('s'),
            '\u{212A}' => saida.push('k'),
            '\u{212B}' => saida.push('a'),
            outro => saida.extend(outro.to_lowercase()),
        }
    }
    saida
}

pub fn py_json_dumps(py: Python<'_>, objeto: &Bound<'_, PyAny>) -> PyResult<String> {
    py.import("json")?
        .call_method1("dumps", (objeto,))?
        .extract()
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn basename_retorna_nome_do_arquivo() {
        assert_eq!(basename("/a/b/c.txt"), "c.txt");
        assert_eq!(basename("c.txt"), "c.txt");
        assert_eq!(basename("/a/b/"), "");
    }

    #[test]
    fn extension_of_retorna_extensao_minuscula_com_ponto() {
        assert_eq!(extension_of("/a/b/Notas.MD"), ".md");
        assert_eq!(extension_of("/a/b/sem_extensao"), "");
    }

    #[test]
    fn casefold_normaliza_como_o_python() {
        assert_eq!(casefold("Straße"), "strasse");
        assert_eq!(casefold("ÁÉÍ"), "áéí");
        assert_eq!(casefold("ﬁ"), "fi");
        assert_eq!(casefold("K"), "k");
    }

    #[test]
    fn path_from_root_monta_caminho_sob_a_raiz() {
        let _guarda = crate::teste_util::lock_global();
        definir_raiz("/raiz".to_string());
        assert!(path_from_root(&["ui", "estilo"]).ends_with("ui/estilo"));
    }
}
