use std::collections::HashSet;
use std::sync::OnceLock;

use pyo3::prelude::*;
use pyo3::types::PyFrozenSet;

pub const BINARY_EXTENSIONS: &[&str] = &[
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tiff", ".svg",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".ogv",
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".dat", ".o", ".a", ".lib",
];

pub const IGNORED_DIRS: &[&str] = &[
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".cache", "cacheuser", "bin", ".bin", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache", ".eggs",
    "site-packages", ".npm", ".yarn",
];

pub const GLOBAL_SEARCH_MAX_MATCHES: i64 = 5000;
pub const FILE_NAME_SEARCH_MAX_RESULTS: i64 = 1000;
pub const SEARCH_BATCH_SIZE: i64 = 30;
pub const GIT_STATUS_DEBOUNCE_MS: i64 = 300;

static BINARY_SET: OnceLock<HashSet<&'static str>> = OnceLock::new();
static IGNORED_SET: OnceLock<HashSet<&'static str>> = OnceLock::new();

pub fn is_binary_extension(extension: &str) -> bool {
    BINARY_SET
        .get_or_init(|| BINARY_EXTENSIONS.iter().copied().collect())
        .contains(extension)
}

pub fn is_ignored_dir(name: &str) -> bool {
    IGNORED_SET
        .get_or_init(|| IGNORED_DIRS.iter().copied().collect())
        .contains(name)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add("BINARY_EXTENSIONS", PyFrozenSet::new(py, BINARY_EXTENSIONS)?)?;
    m.add("IGNORED_DIRS", PyFrozenSet::new(py, IGNORED_DIRS)?)?;
    m.add("GLOBAL_SEARCH_MAX_MATCHES", GLOBAL_SEARCH_MAX_MATCHES)?;
    m.add("FILE_NAME_SEARCH_MAX_RESULTS", FILE_NAME_SEARCH_MAX_RESULTS)?;
    m.add("SEARCH_BATCH_SIZE", SEARCH_BATCH_SIZE)?;
    m.add("GIT_STATUS_DEBOUNCE_MS", GIT_STATUS_DEBOUNCE_MS)?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn reconhece_extensoes_binarias() {
        assert!(is_binary_extension(".png"));
        assert!(is_binary_extension(".exe"));
        assert!(!is_binary_extension(".py"));
        assert!(!is_binary_extension(".PNG"));
    }

    #[test]
    fn reconhece_diretorios_ignorados() {
        assert!(is_ignored_dir(".git"));
        assert!(is_ignored_dir("__pycache__"));
        assert!(!is_ignored_dir("src"));
    }

    #[test]
    fn constantes_publicadas_estao_completas() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            assert!(modulo.getattr("BINARY_EXTENSIONS").unwrap().len().unwrap() > 0);
            assert!(modulo.getattr("IGNORED_DIRS").unwrap().len().unwrap() > 0);
            assert_eq!(
                modulo.getattr("GLOBAL_SEARCH_MAX_MATCHES").unwrap().extract::<i64>().unwrap(),
                GLOBAL_SEARCH_MAX_MATCHES
            );
        });
    }
}
