use std::fs;
use std::path::Path;

use pyo3::prelude::*;

use crate::constants;
use crate::runtime;

pub fn ler_arquivo(file_path: &str) -> String {
    if !Path::new(file_path).exists() {
        return String::new();
    }

    if constants::is_binary_extension(&runtime::extension_of(file_path)) {
        return String::new();
    }

    match fs::read(file_path) {
        Ok(bytes) => match String::from_utf8(bytes) {
            Ok(texto) => texto,
            Err(erro) => {
                println!("[BufferManager] Erro ao ler '{}': {}", file_path, erro);
                String::new()
            }
        },
        Err(erro) => {
            println!("[BufferManager] Erro ao ler '{}': {}", file_path, erro);
            String::new()
        }
    }
}

pub fn salvar_arquivo(file_path: &str, content: &str) -> bool {
    let caminho = Path::new(file_path);
    let pai = caminho.parent().map(|p| p.as_os_str().to_owned());

    match pai {
        Some(pai) if pai.is_empty() => {
            println!("[BufferManager] Erro ao salvar '{}': arquivo sem diretório", file_path);
            return false;
        }
        Some(pai) => {
            if let Err(erro) = fs::create_dir_all(Path::new(&pai)) {
                println!("[BufferManager] Erro ao salvar '{}': {}", file_path, erro);
                return false;
            }
        }
        None => {
            println!("[BufferManager] Erro ao salvar '{}': caminho inválido", file_path);
            return false;
        }
    }

    match fs::write(caminho, content) {
        Ok(()) => true,
        Err(erro) => {
            println!("[BufferManager] Erro ao salvar '{}': {}", file_path, erro);
            false
        }
    }
}

pub fn extensao(file_path: &str) -> String {
    match Path::new(file_path).extension() {
        Some(ext) => format!(".{}", ext.to_string_lossy()),
        None => String::new(),
    }
}

#[pyclass]
pub struct BufferManager;

#[pymethods]
impl BufferManager {
    #[staticmethod]
    fn read_file(file_path: String) -> String {
        ler_arquivo(&file_path)
    }

    #[staticmethod]
    fn save_file(file_path: String, content: String) -> bool {
        salvar_arquivo(&file_path, &content)
    }

    #[staticmethod]
    fn get_file_extension(file_path: String) -> String {
        extensao(&file_path)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<BufferManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn ler_arquivo_retorna_vazio_para_inexistente() {
        assert_eq!(ler_arquivo("/nao/existe/arquivo.txt"), "");
    }

    #[test]
    fn ler_arquivo_retorna_vazio_para_binario() {
        let dir = crate::teste_util::dir_temporario("buffer_bin");
        let caminho = dir.join("imagem.png");
        fs::write(&caminho, [0u8, 1, 2, 3]).unwrap();
        assert_eq!(ler_arquivo(&caminho.to_string_lossy()), "");
    }

    #[test]
    fn salvar_e_ler_roundtrip_criando_pastas() {
        let dir = crate::teste_util::dir_temporario("buffer_rt");
        let caminho = dir.join("sub/dir/nota.md");
        assert!(salvar_arquivo(&caminho.to_string_lossy(), "# Olá\n"));
        assert_eq!(ler_arquivo(&caminho.to_string_lossy()), "# Olá\n");
    }

    #[test]
    fn salvar_sem_diretorio_retorna_falso() {
        assert!(!salvar_arquivo("arquivo_soltinho.txt", "x"));
    }

    #[test]
    fn extensao_retorna_com_ponto() {
        assert_eq!(extensao("/a/b/c.PY"), ".PY");
        assert_eq!(extensao("/a/b/c"), "");
    }

    #[test]
    fn api_python_expoe_os_tres_metodos() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let classe = modulo.getattr("BufferManager").unwrap();
            let dir = crate::teste_util::dir_temporario("buffer_py");
            let caminho = dir.join("a/b.txt");
            let caminho = caminho.to_string_lossy().to_string();
            let ok: bool = classe
                .call_method1("save_file", (&caminho, "conteúdo"))
                .unwrap()
                .extract()
                .unwrap();
            assert!(ok);
            let texto: String = classe
                .call_method1("read_file", (&caminho,))
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(texto, "conteúdo");
            let ext: String = classe
                .call_method1("get_file_extension", (&caminho,))
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(ext, ".txt");
        });
    }
}
