use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

pub const SYSTEM_PYTHON: &str = "/usr/bin/python3";
pub const SYSTEM_DIALOG_TIMEOUT: i64 = 300;

pub const SYSTEM_DIALOG_SCRIPT: &str = r#"
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import gi
    from gi.repository import Gio, GLib
    from urllib.parse import unquote, urlparse
    import uuid
except Exception:
    sys.stdout.write("NOTOHIS_DIALOG_UNAVAILABLE")
    sys.exit(0)

initial = sys.argv[1] if len(sys.argv) > 1 else ""
wait_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 300
outcome = ["NOTOHIS_DIALOG_TIMEOUT"]
loop = GLib.MainLoop()

def on_response(connection, sender, object_path, interface, signal, params, user_data=None):
    try:
        code, results = params.unpack()
    except Exception:
        code, results = 1, {}
    uri = results.get("current_uri") or ""
    if not uri and results.get("uris"):
        uri = results["uris"][0]
    if code == 0 and uri.startswith("file://"):
        outcome[0] = "NOTOHIS_DIALOG_OK " + unquote(urlparse(uri).path)
    else:
        outcome[0] = "NOTOHIS_DIALOG_CANCELLED"
    loop.quit()

try:
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    proxy = Gio.DBusProxy.new_sync(
        bus, Gio.DBusProxyFlags.NONE, None,
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.FileChooser",
        None,
    )
    token = "notohis_" + uuid.uuid4().hex
    options = {
        "directory": GLib.Variant("b", True),
        "modal": GLib.Variant("b", True),
        "handle_token": GLib.Variant("s", token),
    }
    if initial:
        options["current_folder"] = GLib.Variant("ay", bytearray(initial.encode("utf-8") + b"\0"))
    try:
        handle = proxy.call_sync(
            "OpenFile", GLib.Variant("(ssa{sv})", ("", "Abrir projeto", options)),
            Gio.DBusCallFlags.NONE, -1, None,
        )
    except GLib.Error:
        legacy = dict(options, title=GLib.Variant("s", "Abrir projeto"))
        handle = proxy.call_sync(
            "OpenFile", GLib.Variant("(sa{sv})", ("", legacy)),
            Gio.DBusCallFlags.NONE, -1, None,
        )
    for response_interface in ("org.freedesktop.portal.Request", "org.freedesktop.portal.FileChooser"):
        bus.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            response_interface,
            "Response", handle.unpack()[0], None,
            Gio.DBusSignalFlags.NONE, on_response, None,
        )
except Exception:
    sys.stdout.write("NOTOHIS_DIALOG_UNAVAILABLE")
    sys.exit(0)

GLib.timeout_add_seconds(wait_seconds, lambda: (loop.quit(), False)[1])
loop.run()
sys.stdout.write(outcome[0])
"#;

fn interpreter_disponivel() -> Option<String> {
    if Path::new(SYSTEM_PYTHON).exists() {
        return Some(SYSTEM_PYTHON.to_string());
    }

    let caminho = std::env::var("PATH").ok()?;
    for diretorio in caminho.split(':') {
        if diretorio.is_empty() {
            continue;
        }
        let candidato = Path::new(diretorio).join("python3");
        if candidato.exists() {
            return Some(candidato.to_string_lossy().into_owned());
        }
    }
    None
}

#[pyclass]
pub struct FileManager;

#[pymethods]
impl FileManager {
    #[classattr]
    const SYSTEM_PYTHON: &'static str = SYSTEM_PYTHON;

    #[classattr]
    const SYSTEM_DIALOG_TIMEOUT: i64 = SYSTEM_DIALOG_TIMEOUT;

    #[classattr]
    const SYSTEM_DIALOG_SCRIPT: &'static str = SYSTEM_DIALOG_SCRIPT;

    #[staticmethod]
    fn list_directory(py: Python<'_>, path: String) -> PyResult<Py<PyAny>> {
        let raiz = Path::new(&path);
        let itens = PyList::empty(py);

        if path.is_empty() || !raiz.exists() {
            return Ok(itens.unbind().into_any());
        }

        let mut entradas: Vec<(bool, String, String)> = Vec::new();

        match fs::read_dir(raiz) {
            Ok(leitura) => {
                for entrada in leitura.flatten() {
                    let nome = entrada.file_name().to_string_lossy().into_owned();
                    let eh_dir = fs::metadata(entrada.path()).map(|m| m.is_dir()).unwrap_or(false);
                    entradas.push((eh_dir, nome, entrada.path().to_string_lossy().into_owned()));
                }
            }
            Err(erro) => {
                if erro.kind() == std::io::ErrorKind::PermissionDenied {
                    println!("[FileManager] Sem permissão para listar: {}", path);
                } else {
                    println!("[FileManager] Erro ao listar '{}': {}", path, erro);
                }
                return Ok(itens.unbind().into_any());
            }
        }

        entradas.sort_by(|a, b| (!a.0).cmp(&!b.0).then_with(|| a.1.to_lowercase().cmp(&b.1.to_lowercase())));

        for (eh_dir, nome, caminho_completo) in entradas {
            let item = PyDict::new(py);
            item.set_item("name", nome)?;
            item.set_item("path", caminho_completo)?;
            item.set_item("is_dir", eh_dir)?;
            itens.append(item)?;
        }

        Ok(itens.unbind().into_any())
    }

    #[staticmethod]
    #[pyo3(signature = (initialdir = None))]
    fn ask_system_directory(initialdir: Option<String>) -> Option<String> {
        let interpretador = match interpreter_disponivel() {
            Some(interpretador) => interpretador,
            None => return None,
        };

        let inicial = initialdir.unwrap_or_default();
        let mut comando = Command::new(&interpretador);
        comando
            .arg("-c")
            .arg(SYSTEM_DIALOG_SCRIPT)
            .arg(&inicial)
            .arg(SYSTEM_DIALOG_TIMEOUT.to_string())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());

        let mut processo = match comando.spawn() {
            Ok(processo) => processo,
            Err(_) => return None,
        };

        let limite = Instant::now() + Duration::from_secs(SYSTEM_DIALOG_TIMEOUT as u64 + 20);
        loop {
            match processo.try_wait() {
                Ok(Some(_)) => break,
                Ok(None) => {
                    if Instant::now() >= limite {
                        let _ = processo.kill();
                        let _ = processo.wait();
                        return None;
                    }
                    thread::sleep(Duration::from_millis(50));
                }
                Err(_) => return None,
            }
        }

        let mut saida = String::new();
        if let Some(mut stdout) = processo.stdout.take() {
            let _ = std::io::Read::read_to_string(&mut stdout, &mut saida);
        }

        let saida = saida.trim().to_string();
        let prefixo = "NOTOHIS_DIALOG_OK ";

        if let Some(caminho) = saida.strip_prefix(prefixo) {
            if caminho.is_empty() {
                return None;
            }
            return Some(caminho.to_string());
        }

        if saida == "NOTOHIS_DIALOG_CANCELLED" || saida == "NOTOHIS_DIALOG_TIMEOUT" {
            return Some(String::new());
        }

        None
    }

    #[staticmethod]
    fn create_file(path: String) -> bool {
        let pai = Path::new(&path).parent().map(|p| p.as_os_str().to_owned());

        let diretorio = match pai {
            Some(pai) if pai.is_empty() => {
                println!("[FileManager] Erro ao criar arquivo '{}': arquivo sem diretório", path);
                return false;
            }
            Some(pai) => Path::new(&pai).to_path_buf(),
            None => {
                println!("[FileManager] Erro ao criar arquivo '{}': caminho inválido", path);
                return false;
            }
        };

        match fs::create_dir_all(&diretorio) {
            Ok(()) => match fs::OpenOptions::new().write(true).create(true).truncate(true).open(&path) {
                Ok(_) => true,
                Err(erro) => {
                    println!("[FileManager] Erro ao criar arquivo '{}': {}", path, erro);
                    false
                }
            },
            Err(erro) => {
                println!("[FileManager] Erro ao criar arquivo '{}': {}", path, erro);
                false
            }
        }
    }

    #[staticmethod]
    fn create_directory(path: String) -> bool {
        match fs::create_dir_all(&path) {
            Ok(()) => true,
            Err(erro) => {
                println!("[FileManager] Erro ao criar diretório '{}': {}", path, erro);
                false
            }
        }
    }

    #[staticmethod]
    fn rename_path(old_path: String, new_name: String) -> bool {
        let pai = Path::new(&old_path).parent().unwrap_or(Path::new(""));
        let destino = pai.join(&new_name);

        match fs::rename(&old_path, &destino) {
            Ok(()) => true,
            Err(erro) => {
                println!(
                    "[FileManager] Erro ao renomear '{}' para '{}': {}",
                    old_path, new_name, erro
                );
                false
            }
        }
    }

    #[staticmethod]
    fn delete_path(path: String) -> bool {
        let alvo = Path::new(&path);

        let resultado = if alvo.is_dir() {
            fs::remove_dir_all(alvo)
        } else {
            fs::remove_file(alvo)
        };

        match resultado {
            Ok(()) => true,
            Err(erro) => {
                println!("[FileManager] Erro ao excluir '{}': {}", path, erro);
                false
            }
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FileManager>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    fn criar_arvore(base: &Path) {
        fs::create_dir_all(base.join("docs")).unwrap();
        fs::create_dir_all(base.join("src")).unwrap();
        fs::write(base.join("b.txt"), "b").unwrap();
        fs::write(base.join("docs/a.md"), "a").unwrap();
    }

    #[test]
    fn list_directory_ordena_pastas_depois_arquivos() {
        Python::attach(|py| {
            let dir = crate::teste_util::dir_temporario("fm_list");
            criar_arvore(&dir);
            let lista = FileManager::list_directory(py, dir.to_string_lossy().to_string()).unwrap();
            let lista = lista.bind(py).cast::<PyList>().unwrap();
            assert_eq!(lista.len(), 3);
            let nomes: Vec<String> = (0..lista.len())
                .map(|i| {
                    lista.get_item(i).unwrap().get_item("name").unwrap().extract().unwrap()
                })
                .collect();
            assert_eq!(nomes, vec!["docs", "src", "b.txt"]);
            let eh_dir: bool = lista.get_item(0).unwrap().get_item("is_dir").unwrap().extract().unwrap();
            assert!(eh_dir);
        });
    }

    #[test]
    fn list_directory_inexistente_ou_vazio_retorna_lista_vazia() {
        Python::attach(|py| {
            let vazia = FileManager::list_directory(py, "".to_string()).unwrap();
            assert_eq!(vazia.bind(py).cast::<PyList>().unwrap().len(), 0);
            let inexistente = FileManager::list_directory(py, "/nao/existe/dir".to_string()).unwrap();
            assert_eq!(inexistente.bind(py).cast::<PyList>().unwrap().len(), 0);
        });
    }

    #[test]
    fn create_file_cria_pais_e_arquivo_vazio() {
        let dir = crate::teste_util::dir_temporario("fm_create");
        let alvo = dir.join("x/y/nota.txt");
        assert!(FileManager::create_file(alvo.to_string_lossy().to_string()));
        assert!(alvo.exists());
        assert_eq!(fs::read_to_string(&alvo).unwrap(), "");
    }

    #[test]
    fn create_directory_cria_recursivamente() {
        let dir = crate::teste_util::dir_temporario("fm_mkdir");
        let alvo = dir.join("a/b/c");
        assert!(FileManager::create_directory(alvo.to_string_lossy().to_string()));
        assert!(alvo.is_dir());
    }

    #[test]
    fn rename_path_move_no_mesmo_diretorio() {
        let dir = crate::teste_util::dir_temporario("fm_rename");
        let origem = dir.join("velho.txt");
        fs::write(&origem, "conteúdo").unwrap();
        assert!(FileManager::rename_path(origem.to_string_lossy().to_string(), "novo.txt".to_string()));
        assert!(dir.join("novo.txt").exists());
        assert!(!origem.exists());
    }

    #[test]
    fn delete_path_remove_arquivo_e_diretorio() {
        let dir = crate::teste_util::dir_temporario("fm_delete");
        let arquivo = dir.join("f.txt");
        fs::write(&arquivo, "x").unwrap();
        assert!(FileManager::delete_path(arquivo.to_string_lossy().to_string()));
        assert!(!arquivo.exists());

        let pasta = dir.join("pasta");
        fs::create_dir_all(pasta.join("interna")).unwrap();
        assert!(FileManager::delete_path(pasta.to_string_lossy().to_string()));
        assert!(!pasta.exists());
    }

    #[test]
    fn operacoes_com_caminho_invalido_retornam_falso() {
        assert!(!FileManager::create_file("".to_string()));
        assert!(!FileManager::delete_path("/nao/existe/nada.txt".to_string()));
        assert!(!FileManager::rename_path("/nao/existe/nada.txt".to_string(), "x".to_string()));
    }

    #[test]
    fn constantes_do_dialogo_estao_como_na_versao_python() {
        assert_eq!(FileManager::SYSTEM_PYTHON, "/usr/bin/python3");
        assert_eq!(FileManager::SYSTEM_DIALOG_TIMEOUT, 300);
        assert!(FileManager::SYSTEM_DIALOG_SCRIPT.contains("import gi"));
        assert!(FileManager::SYSTEM_DIALOG_SCRIPT.contains("NOTOHIS_DIALOG_OK "));
        assert!(FileManager::SYSTEM_DIALOG_SCRIPT.contains("NOTOHIS_DIALOG_CANCELLED"));
        assert!(FileManager::SYSTEM_DIALOG_SCRIPT.contains("NOTOHIS_DIALOG_TIMEOUT"));
    }
}
