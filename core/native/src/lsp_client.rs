use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::process::{ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::runtime;

struct Compartilhado {
    callbacks: Mutex<HashMap<String, Py<PyAny>>>,
    responses: Mutex<HashMap<String, Py<PyAny>>>,
}

#[pyclass]
pub struct LSPProcess {
    #[pyo3(get)]
    pid: i32,
}

#[pyclass]
pub struct LSPClient {
    #[pyo3(get)]
    server_command: Vec<String>,
    processo: Mutex<Option<Py<LSPProcess>>>,
    pid: Mutex<Option<i32>>,
    stdin: Mutex<Option<ChildStdin>>,
    request_id: AtomicI64,
    compartilhado: Arc<Compartilhado>,
}

impl LSPClient {
    pub fn novo(server_command: Vec<String>) -> Self {
        LSPClient {
            server_command,
            processo: Mutex::new(None),
            pid: Mutex::new(None),
            stdin: Mutex::new(None),
            request_id: AtomicI64::new(0),
            compartilhado: Arc::new(Compartilhado {
                callbacks: Mutex::new(HashMap::new()),
                responses: Mutex::new(HashMap::new()),
            }),
        }
    }
}

fn montar_corpo(py: Python<'_>, campos: &[(&str, Py<PyAny>)]) -> PyResult<String> {
    let conteudo = PyDict::new(py);
    for (chave, valor) in campos {
        conteudo.set_item(*chave, valor)?;
    }
    runtime::py_json_dumps(py, &conteudo.into_any())
}

fn escrever_mensagem(stdin: &mut ChildStdin, corpo: &str) -> std::io::Result<()> {
    let cabecalho = format!("Content-Length: {}\r\n\r\n", corpo.len());
    stdin.write_all(cabecalho.as_bytes())?;
    stdin.write_all(corpo.as_bytes())?;
    stdin.flush()
}

#[pymethods]
impl LSPClient {
    #[new]
    fn new(server_command: Vec<String>) -> Self {
        Self::novo(server_command)
    }

    #[getter]
    fn process(&self, py: Python<'_>) -> Option<Py<LSPProcess>> {
        self.processo
            .lock()
            .unwrap()
            .as_ref()
            .map(|processo| processo.clone_ref(py))
    }

    pub fn tem_processo(&self) -> bool {
        self.pid.lock().unwrap().is_some()
    }

    pub fn start(&self, py: Python<'_>) -> PyResult<()> {
        let Some(executavel) = self.server_command.first() else {
            println!("[LSP] Erro ao iniciar servidor: comando vazio");
            return Ok(());
        };

        let mut comando = Command::new(executavel);
        comando
            .args(&self.server_command[1..])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        match comando.spawn() {
            Ok(mut processo) => {
                let pid = processo.id() as i32;
                let stdout: ChildStdout = processo.stdout.take().expect("stdout piped");
                let stdin = processo.stdin.take();

                *self.stdin.lock().unwrap() = stdin;
                *self.pid.lock().unwrap() = Some(pid);
                *self.processo.lock().unwrap() = Some(Py::new(py, LSPProcess { pid })?);

                let compartilhado = Arc::clone(&self.compartilhado);
                thread::spawn(move || laço_leitura(stdout, compartilhado));

                println!("[LSP] Servidor iniciado: {}", self.server_command.join(" "));
            }
            Err(erro) if erro.kind() == std::io::ErrorKind::NotFound => {
                println!(
                    "[LSP] Servidor '{}' não encontrado. Autocompletar inteligente desativado.",
                    executavel
                );
            }
            Err(erro) => {
                println!("[LSP] Erro ao iniciar servidor: {}", erro);
            }
        }
        Ok(())
    }

    #[pyo3(signature = (method, params))]
    pub fn send_notification(&self, py: Python<'_>, method: String, params: Py<PyAny>) -> PyResult<()> {
        let mut stdin_travado = self.stdin.lock().unwrap();
        let Some(stdin) = stdin_travado.as_mut() else {
            return Ok(());
        };

        let corpo = montar_corpo(
            py,
            &[
                ("jsonrpc", "2.0".into_pyobject(py)?.into_any().unbind()),
                ("method", method.clone().into_pyobject(py)?.into_any().unbind()),
                ("params", params),
            ],
        )?;

        match escrever_mensagem(stdin, &corpo) {
            Ok(()) => Ok(()),
            Err(_) => {
                println!(
                    "[LSP] Falha ao enviar notificação {}: Processo não disponível.",
                    method
                );
                Ok(())
            }
        }
    }

    #[pyo3(signature = (method, params, callback = None))]
    pub fn send_request(
        &self,
        py: Python<'_>,
        method: String,
        params: Py<PyAny>,
        callback: Option<Py<PyAny>>,
    ) -> PyResult<Option<i64>> {
        let mut stdin_travado = self.stdin.lock().unwrap();
        let Some(stdin) = stdin_travado.as_mut() else {
            return Ok(None);
        };

        let requisicao = self.request_id.fetch_add(1, Ordering::SeqCst) + 1;
        if let Some(callback) = callback {
            self.compartilhado
                .callbacks
                .lock()
                .unwrap()
                .insert(requisicao.to_string(), callback);
        }

        let corpo = montar_corpo(
            py,
            &[
                ("jsonrpc", "2.0".into_pyobject(py)?.into_any().unbind()),
                ("id", requisicao.into_pyobject(py)?.into_any().unbind()),
                ("method", method.into_pyobject(py)?.into_any().unbind()),
                ("params", params),
            ],
        )?;

        match escrever_mensagem(stdin, &corpo) {
            Ok(()) => (),
            Err(erro) => println!("[LSP] Erro de escrita no servidor: {}", erro),
        }
        Ok(Some(requisicao))
    }

    fn stop(&self) {
        let pid = *self.pid.lock().unwrap();
        if let Some(pid) = pid {
            unsafe {
                libc::kill(pid, libc::SIGTERM);
            }
        }
    }
}

fn laço_leitura(stdout: ChildStdout, compartilhado: Arc<Compartilhado>) {
    let mut leitor = BufReader::new(stdout);
    loop {
        let mut linha = String::new();
        match leitor.read_line(&mut linha) {
            Ok(0) | Err(_) => return,
            Ok(_) => (),
        }
        if !linha.starts_with("Content-Length:") {
            continue;
        }
        let comprimento = linha
            .split(':')
            .nth(1)
            .and_then(|parte| parte.trim().parse::<usize>().ok());
        let Some(comprimento) = comprimento else {
            return;
        };

        let mut pular = String::new();
        let _ = leitor.read_line(&mut pular);
        let mut conteudo = vec![0u8; comprimento];
        if leitor.read_exact(&mut conteudo).is_err() {
            return;
        }

        let Ok(texto) = std::str::from_utf8(&conteudo) else {
            return;
        };
        let Ok(mensagem) = serde_json::from_str::<serde_json::Value>(texto) else {
            return;
        };
        let Some(id) = mensagem.get("id") else {
            continue;
        };
        let chave = id.to_string();

        let callback = compartilhado.callbacks.lock().unwrap().remove(&chave);
        let python_objeto = Python::attach(|py| runtime::py_json_loads(py, mensagem.to_string()));

        match callback {
            Some(callback) => {
                let Ok(objeto) = python_objeto else { return };
                let falhou = Python::attach(|py| callback.call1(py, (objeto,)).is_err());
                if falhou {
                    return;
                }
            }
            None => {
                if let Ok(objeto) = python_objeto {
                    compartilhado
                        .responses
                        .lock()
                        .unwrap()
                        .insert(chave, objeto);
                }
            }
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<LSPClient>()?;
    m.add_class::<LSPProcess>()?;
    Ok(())
}
