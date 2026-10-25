use std::collections::{HashMap, VecDeque};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use pyo3::exceptions::{PyOSError, PyRuntimeError};
use pyo3::prelude::*;

use crate::breakpoints::PontosDeParada;
use crate::protocol::{serializar, Comando, Evento};

const LIMITE_EVENTOS: usize = 20000;
const TEMPO_CONEXAO: Duration = Duration::from_secs(6);
const TEMPO_RESPOSTA: Duration = Duration::from_millis(1500);

fn erro_io(erro: std::io::Error) -> PyErr {
    PyOSError::new_err(erro.to_string())
}

fn enfileirar(eventos: &Arc<Mutex<VecDeque<String>>>, texto: String) {
    let mut fila = eventos.lock().unwrap();
    if fila.len() >= LIMITE_EVENTOS {
        fila.pop_front();
    }
    fila.push_back(texto);
}

fn caminho_pythonpath(diretorio_runtime: &str) -> String {
    let mut entradas = vec![PathBuf::from(diretorio_runtime)];
    if let Ok(atual) = std::env::var("PYTHONPATH") {
        entradas.extend(std::env::split_paths(&atual));
    }
    std::env::join_paths(entradas)
        .map(|caminho| caminho.to_string_lossy().into_owned())
        .unwrap_or_else(|_| diretorio_runtime.to_string())
}

#[pyclass]
pub struct SessaoDeDepuracao {
    porta: u16,
    ouvinte: Mutex<Option<TcpListener>>,
    escrita: Mutex<Option<TcpStream>>,
    filho: Arc<Mutex<Option<Child>>>,
    eventos: Arc<Mutex<VecDeque<String>>>,
    respostas: Arc<Mutex<HashMap<u64, String>>>,
    espera_resposta: Arc<Condvar>,
    proximo_id: AtomicU64,
    pontos: Mutex<PontosDeParada>,
    estado: Arc<Mutex<String>>,
}

impl SessaoDeDepuracao {
    fn aguardar_conexao(&self) -> PyResult<TcpStream> {
        let inicio = Instant::now();
        loop {
            {
                let ouvinte = self.ouvinte.lock().unwrap();
                if let Some(alvo) = ouvinte.as_ref() {
                    match alvo.accept() {
                        Ok((fluxo, _)) => return Ok(fluxo),
                        Err(erro) if erro.kind() == std::io::ErrorKind::WouldBlock => {}
                        Err(erro) => return Err(erro_io(erro)),
                    }
                }
            }
            if self.filho_saiu() {
                return Err(PyRuntimeError::new_err(
                    "o processo debugado encerrou antes de conectar",
                ));
            }
            if inicio.elapsed() > TEMPO_CONEXAO {
                return Err(PyRuntimeError::new_err(
                    "tempo esgotado aguardando o processo debugado",
                ));
            }
            thread::sleep(Duration::from_millis(20));
        }
    }

    fn filho_saiu(&self) -> bool {
        let mut guarda = self.filho.lock().unwrap();
        match guarda.as_mut() {
            Some(filho) => matches!(filho.try_wait(), Ok(Some(_)) | Err(_)),
            None => true,
        }
    }

    fn conectar_escrita(&self, conexao: &TcpStream) -> PyResult<()> {
        conexao.set_nonblocking(false).map_err(erro_io)?;
        conexao.set_read_timeout(None).map_err(erro_io)?;
        let escrita = conexao.try_clone().map_err(erro_io)?;
        *self.escrita.lock().unwrap() = Some(escrita);
        Ok(())
    }

    fn iniciar_leitor(&self, fluxo: TcpStream) {
        let eventos = Arc::clone(&self.eventos);
        let respostas = Arc::clone(&self.respostas);
        let espera = Arc::clone(&self.espera_resposta);
        let estado = Arc::clone(&self.estado);
        thread::spawn(move || {
            let mut linhas = BufReader::new(fluxo).lines();
            while let Some(Ok(linha)) = linhas.next() {
                if linha.trim().is_empty() {
                    continue;
                }
                let Ok(evento) = serde_json::from_str::<Evento>(&linha) else {
                    continue;
                };
                match &evento {
                    Evento::Variaveis { id, .. } | Evento::Avaliado { id, .. } => {
                        respostas.lock().unwrap().insert(*id, linha);
                        espera.notify_all();
                    }
                    Evento::Parado { .. } => {
                        *estado.lock().unwrap() = String::from("parado");
                        enfileirar(&eventos, linha);
                    }
                    Evento::Continuado => {
                        *estado.lock().unwrap() = String::from("executando");
                        enfileirar(&eventos, linha);
                    }
                    _ => enfileirar(&eventos, linha),
                }
            }
        });
    }

    fn vigiar_entrada(&self, fluxo: impl Read + Send + 'static, rotulo: &str) {
        let eventos = Arc::clone(&self.eventos);
        let rotulo = rotulo.to_string();
        thread::spawn(move || {
            let mut leitor = BufReader::new(fluxo);
            let mut buffer: Vec<u8> = Vec::new();
            loop {
                buffer.clear();
                match leitor.read_until(b'\n', &mut buffer) {
                    Ok(0) => break,
                    Ok(_) => {
                        if buffer.is_empty() {
                            continue;
                        }
                        let evento = Evento::Saida {
                            fluxo: rotulo.clone(),
                            texto: String::from_utf8_lossy(&buffer).into_owned(),
                        };
                        if let Some(json) = serializar(&evento) {
                            enfileirar(&eventos, json);
                        }
                    }
                    Err(_) => break,
                }
            }
        });
    }

    fn vigiar_filho(&self) {
        let filho = Arc::clone(&self.filho);
        let eventos = Arc::clone(&self.eventos);
        let estado = Arc::clone(&self.estado);
        thread::spawn(move || loop {
            thread::sleep(Duration::from_millis(50));
            let mut guarda = filho.lock().unwrap();
            match guarda.as_mut() {
                None => break,
                Some(processo) => match processo.try_wait() {
                    Ok(None) => {}
                    Ok(Some(situacao)) => {
                        let codigo = situacao.code().unwrap_or(-1);
                        if let Some(json) = serializar(&Evento::Saiu { codigo }) {
                            enfileirar(&eventos, json);
                        }
                        *estado.lock().unwrap() = String::from("encerrado");
                        *guarda = None;
                        break;
                    }
                    Err(_) => break,
                },
            }
        });
    }

    fn aguardar_resposta(
        &self,
        py: Python<'_>,
        id: u64,
        limite: Duration,
    ) -> Option<String> {
        py.detach(|| {
            let mut guarda = self.respostas.lock().unwrap();
            let fim = Instant::now() + limite;
            while !guarda.contains_key(&id) {
                let restante = fim.checked_duration_since(Instant::now())?;
                guarda = self
                    .espera_resposta
                    .wait_timeout(guarda, restante)
                    .ok()?
                    .0;
            }
            guarda.remove(&id)
        })
    }

    fn conectado(&self) -> bool {
        self.escrita.lock().unwrap().is_some()
    }

    fn enviar(&self, comando: &Comando) -> PyResult<()> {
        let Some(texto) = serializar(comando) else {
            return Ok(());
        };
        let mut guarda = self.escrita.lock().unwrap();
        let Some(fluxo) = guarda.as_mut() else {
            return Ok(());
        };
        let resultado = writeln!(fluxo, "{}", texto).and_then(|_| fluxo.flush());
        if resultado.is_err() {
            *guarda = None;
        }
        Ok(())
    }

    fn enviar_pontos(&self) -> PyResult<()> {
        let lista = self.pontos.lock().unwrap().todos();
        for (arquivo, linhas) in lista {
            self.enviar(&Comando::DefinirPontos { arquivo, linhas })?;
        }
        Ok(())
    }

    fn encerrar_filho(&self) {
        let mut guarda = self.filho.lock().unwrap();
        if let Some(mut filho) = guarda.take() {
            let _ = filho.kill();
            let _ = filho.wait();
        }
    }

    fn pedir(&self, py: Python<'_>, comando: Comando, id: u64) -> PyResult<Option<String>> {
        if !self.conectado() {
            return Ok(None);
        }
        self.enviar(&comando)?;
        if !self.conectado() {
            return Ok(None);
        }
        Ok(self.aguardar_resposta(py, id, TEMPO_RESPOSTA))
    }

    fn novo_id(&self) -> u64 {
        self.proximo_id.fetch_add(1, Ordering::SeqCst) + 1
    }

    fn estado_interno(&self) -> String {
        self.estado.lock().unwrap().clone()
    }
}

#[pymethods]
impl SessaoDeDepuracao {
    #[new]
    pub fn novo() -> PyResult<Self> {
        let ouvinte = TcpListener::bind(("127.0.0.1", 0)).map_err(erro_io)?;
        ouvinte.set_nonblocking(true).map_err(erro_io)?;
        let porta = ouvinte.local_addr().map_err(erro_io)?.port();
        Ok(SessaoDeDepuracao {
            porta,
            ouvinte: Mutex::new(Some(ouvinte)),
            escrita: Mutex::new(None),
            filho: Arc::new(Mutex::new(None)),
            eventos: Arc::new(Mutex::new(VecDeque::new())),
            respostas: Arc::new(Mutex::new(HashMap::new())),
            espera_resposta: Arc::new(Condvar::new()),
            proximo_id: AtomicU64::new(0),
            pontos: Mutex::new(PontosDeParada::novo()),
            estado: Arc::new(Mutex::new(String::from("inativo"))),
        })
    }

    #[getter]
    pub fn porta(&self) -> u16 {
        self.porta
    }

    #[getter]
    pub fn estado(&self) -> String {
        self.estado_interno()
    }

    #[pyo3(signature = (caminho, argumentos, executavel, diretorio_runtime))]
    pub fn iniciar(
        &self,
        py: Python<'_>,
        caminho: String,
        argumentos: Vec<String>,
        executavel: String,
        diretorio_runtime: String,
    ) -> PyResult<bool> {
        self.encerrar_filho();
        let execucao = Path::new(&diretorio_runtime).join("target_runner.py");
        if !execucao.is_file() {
            return Err(PyRuntimeError::new_err(format!(
                "não encontrei {}",
                execucao.display()
            )));
        }
        let diretorio_alvo = Path::new(&caminho)
            .parent()
            .map(|pasta| pasta.to_path_buf())
            .unwrap_or_else(|| PathBuf::from("."));
        let mut comando = Command::new(&executavel);
        comando
            .arg(&execucao)
            .arg(&caminho)
            .arg(self.porta.to_string())
            .args(&argumentos)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .current_dir(&diretorio_alvo)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONPATH", caminho_pythonpath(&diretorio_runtime));
        let mut filho = comando
            .spawn()
            .map_err(|erro| PyRuntimeError::new_err(format!("não consegui lançar o alvo: {}", erro)))?;
        let stdout = filho.stdout.take();
        let stderr = filho.stderr.take();
        *self.filho.lock().unwrap() = Some(filho);
        *self.estado.lock().unwrap() = String::from("executando");

        let conexao = py.detach(|| self.aguardar_conexao())?;
        self.conectar_escrita(&conexao)?;
        if let Some(fluxo) = stdout {
            self.vigiar_entrada(fluxo, "stdout");
        }
        if let Some(fluxo) = stderr {
            self.vigiar_entrada(fluxo, "stderr");
        }
        self.vigiar_filho();
        self.iniciar_leitor(conexao);
        self.enviar_pontos()?;
        self.enviar(&Comando::Pronto)?;
        Ok(true)
    }

    pub fn continuar(&self) -> PyResult<()> {
        *self.estado.lock().unwrap() = String::from("executando");
        self.enviar(&Comando::Continuar)
    }

    pub fn pausar(&self) -> PyResult<()> {
        *self.estado.lock().unwrap() = String::from("executando");
        self.enviar(&Comando::Pausar)
    }

    pub fn passo_sobre(&self) -> PyResult<()> {
        *self.estado.lock().unwrap() = String::from("executando");
        self.enviar(&Comando::PassoSobre)
    }

    pub fn passo_dentro(&self) -> PyResult<()> {
        *self.estado.lock().unwrap() = String::from("executando");
        self.enviar(&Comando::PassoDentro)
    }

    pub fn passo_fora(&self) -> PyResult<()> {
        *self.estado.lock().unwrap() = String::from("executando");
        self.enviar(&Comando::PassoFora)
    }

    pub fn parar(&self) -> PyResult<()> {
        self.enviar(&Comando::Encerrar)?;
        *self.escrita.lock().unwrap() = None;
        self.encerrar_filho();
        *self.estado.lock().unwrap() = String::from("encerrado");
        Ok(())
    }

    #[pyo3(signature = (arquivo, linha))]
    pub fn alternar_ponto(&self, arquivo: String, linha: usize) -> PyResult<bool> {
        let (adicionou, linhas) = {
            let mut pontos = self.pontos.lock().unwrap();
            let adicionou = pontos.alternar(&arquivo, linha);
            (adicionou, pontos.linhas(&arquivo))
        };
        self.enviar(&Comando::DefinirPontos { arquivo, linhas })?;
        Ok(adicionou)
    }

    #[pyo3(signature = (arquivo, linhas))]
    pub fn definir_pontos(&self, arquivo: String, linhas: Vec<usize>) -> PyResult<()> {
        self.pontos.lock().unwrap().definir(&arquivo, &linhas);
        self.enviar(&Comando::DefinirPontos { arquivo, linhas })
    }

    pub fn pontos_do_arquivo(&self, arquivo: String) -> Vec<usize> {
        self.pontos.lock().unwrap().linhas(&arquivo)
    }

    pub fn todos_os_pontos(&self) -> Vec<(String, Vec<usize>)> {
        self.pontos.lock().unwrap().todos()
    }

    pub fn limpar_pontos(&self) -> PyResult<()> {
        let anteriores = {
            let mut pontos = self.pontos.lock().unwrap();
            let lista = pontos.todos();
            pontos.limpar();
            lista
        };
        for (arquivo, _) in anteriores {
            self.enviar(&Comando::DefinirPontos {
                arquivo,
                linhas: Vec::new(),
            })?;
        }
        Ok(())
    }

    #[pyo3(signature = (quadro = 0))]
    pub fn pedir_variaveis(&self, py: Python<'_>, quadro: usize) -> PyResult<Option<String>> {
        let id = self.novo_id();
        self.pedir(py, Comando::Variaveis { id, quadro }, id)
    }

    #[pyo3(signature = (expressao, quadro = 0))]
    pub fn pedir_avaliacao(
        &self,
        py: Python<'_>,
        expressao: String,
        quadro: usize,
    ) -> PyResult<Option<String>> {
        let id = self.novo_id();
        self.pedir(
            py,
            Comando::Avaliar {
                id,
                quadro,
                expressao,
            },
            id,
        )
    }

    pub fn drenar_eventos(&self) -> Vec<String> {
        let mut fila = self.eventos.lock().unwrap();
        fila.drain(..).collect()
    }
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn nova_sessao_escuta_em_porta_local() {
        let sessao = SessaoDeDepuracao::novo().unwrap();
        assert!(sessao.porta > 0);
        assert_eq!(sessao.estado_interno(), "inativo");
        assert!(sessao.drenar_eventos().is_empty());
        assert!(!sessao.conectado());
    }

    #[test]
    fn pontos_sobrevivem_sem_conexao_ativa() {
        let sessao = SessaoDeDepuracao::novo().unwrap();
        assert!(sessao.alternar_ponto("/a.py".to_string(), 4).unwrap());
        assert!(!sessao.alternar_ponto("/a.py".to_string(), 4).unwrap());
        assert!(sessao.alternar_ponto("/a.py".to_string(), 7).unwrap());
        assert_eq!(sessao.pontos_do_arquivo("/a.py".to_string()), vec![7]);
        sessao.definir_pontos("/b.py".to_string(), vec![2, 9]).unwrap();
        assert_eq!(sessao.pontos_do_arquivo("/b.py".to_string()), vec![2, 9]);
        sessao.limpar_pontos().unwrap();
        assert!(sessao.pontos_do_arquivo("/b.py".to_string()).is_empty());
    }

    #[test]
    fn comandos_sem_canal_sao_inofensivos() {
        Python::attach(|py| {
            let sessao = SessaoDeDepuracao::novo().unwrap();
            sessao.continuar().unwrap();
            sessao.pausar().unwrap();
            sessao.passo_sobre().unwrap();
            sessao.passo_dentro().unwrap();
            sessao.passo_fora().unwrap();
            sessao.parar().unwrap();
            assert_eq!(sessao.estado_interno(), "encerrado");
            assert!(sessao.pedir_variaveis(py, 0).unwrap().is_none());
        });
    }

    #[test]
    fn espera_de_resposta_devolve_o_item_e_desiste_no_tempo() {
        Python::attach(|py| {
            let sessao = SessaoDeDepuracao::novo().unwrap();
            let sem_resposta =
                sessao.aguardar_resposta(py, 99, Duration::from_millis(50));
            assert!(sem_resposta.is_none());

            let resposta =
                "{\"type\":\"avaliado\",\"id\":1,\"resultado\":\"2\",\"erro\":null}".to_string();
            sessao.respostas.lock().unwrap().insert(1, resposta.clone());
            sessao.espera_resposta.notify_all();
            let obtida = sessao.aguardar_resposta(py, 1, Duration::from_secs(2));
            assert_eq!(obtida, Some(resposta));
        });
    }

    #[test]
    fn fila_de_eventos_guarda_ordem_e_tem_teto() {
        let eventos = Arc::new(Mutex::new(VecDeque::new()));
        for indice in 0..(LIMITE_EVENTOS + 5) {
            enfileirar(&eventos, indice.to_string());
        }
        let fila = eventos.lock().unwrap();
        assert_eq!(fila.len(), LIMITE_EVENTOS);
        assert_eq!(fila.front().map(String::as_str), Some("5"));
        assert_eq!(fila.back().map(String::as_str), Some("20004"));
    }

    #[test]
    fn caminho_do_pythonpath_prioriza_o_runtime() {
        let caminho = caminho_pythonpath("/app/tool-nth");
        assert!(caminho.starts_with("/app/tool-nth"));
    }

    #[test]
    fn serializar_comando_usa_o_campo_esperado() {
        let texto = serializar(&Comando::Pronto).unwrap();
        assert!(texto.contains("\"cmd\":\"pronto\""));
    }
}
