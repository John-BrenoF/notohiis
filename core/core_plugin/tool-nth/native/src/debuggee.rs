use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Condvar, Mutex, OnceLock};
use std::time::{Duration, Instant};

use pyo3::exceptions::{PyKeyboardInterrupt, PyOSError, PyRuntimeError, PySystemExit};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyIterator};

use crate::breakpoints::PontosDeParada;
use crate::protocol::{serializar, Comando, Evento, Quadro, Variavel};
use crate::step_engine::{Modo, MotorDePassos};

static ESTADO: OnceLock<Mutex<Estado>> = OnceLock::new();
static ESPERA: OnceLock<Condvar> = OnceLock::new();
static REFERENCIA_TRACE: OnceLock<Py<PyAny>> = OnceLock::new();
static PAUSA_PEDIDA: AtomicBool = AtomicBool::new(false);

const ESPERA_PRONTO: Duration = Duration::from_secs(15);
const LIMITE_VALOR: usize = 220;

enum Retomada {
    Seguir,
    Sair,
}

struct Estado {
    pontos: PontosDeParada,
    motor: MotorDePassos,
    conexao: Option<TcpStream>,
    quadros: Vec<Py<PyAny>>,
    profundidade_parada: usize,
    resumir: bool,
    sair: bool,
    pronto: bool,
    prefixos: Vec<String>,
}

struct Parada {
    motivo: String,
    arquivo: String,
    linha: usize,
    detalhe: Option<String>,
    quadros: Vec<Quadro>,
    objetos: Vec<Py<PyAny>>,
    profundidade: usize,
}

impl Estado {
    fn novo() -> Self {
        Estado {
            pontos: PontosDeParada::novo(),
            motor: MotorDePassos::novo(),
            conexao: None,
            quadros: Vec::new(),
            profundidade_parada: 0,
            resumir: false,
            sair: false,
            pronto: false,
            prefixos: Vec::new(),
        }
    }
}

fn estado() -> &'static Mutex<Estado> {
    ESTADO.get_or_init(|| Mutex::new(Estado::novo()))
}

fn espera() -> &'static Condvar {
    ESPERA.get_or_init(Condvar::new)
}

pub fn guardar_referencia_trace(referencia: Py<PyAny>) {
    let _ = REFERENCIA_TRACE.set(referencia);
}

fn transmitir(evento: &Evento) {
    let Some(texto) = serializar(evento) else {
        return;
    };
    let mut guarda = estado().lock().unwrap();
    if let Some(fluxo) = guarda.conexao.as_mut() {
        let _ = writeln!(fluxo, "{}", texto);
        let _ = fluxo.flush();
    }
}

fn prefixos_snapshot() -> Vec<String> {
    estado().lock().unwrap().prefixos.clone()
}

fn arquivo_em_escopo(arquivo: &str, prefixos: &[String]) -> bool {
    let caminho = Path::new(arquivo);
    !prefixos.iter().any(|prefixo| {
        !prefixo.is_empty() && caminho.starts_with(Path::new(prefixo.as_str()))
    })
}

fn truncar(texto: &str, limite: usize) -> String {
    if texto.chars().count() <= limite {
        return texto.to_string();
    }
    let mut cortado: String = texto.chars().take(limite).collect();
    cortado.push('…');
    cortado
}

fn resumir_valor(py: Python<'_>, valor: &Bound<'_, PyAny>) -> String {
    let texto = py
        .import("builtins")
        .and_then(|builtins| builtins.call_method1("repr", (valor,)))
        .and_then(|repr| repr.extract::<String>())
        .unwrap_or_else(|_| String::from("<sem representação>"));
    truncar(&texto, LIMITE_VALOR)
}

fn nome_tipo(valor: &Bound<'_, PyAny>) -> String {
    valor
        .getattr("__class__")
        .and_then(|classe| classe.getattr("__name__"))
        .and_then(|nome| nome.extract::<String>())
        .unwrap_or_else(|_| String::from("object"))
}

fn extrair_variaveis(py: Python<'_>, quadro: &Py<PyAny>, locais: bool) -> Vec<Variavel> {
    let ligado = quadro.bind(py);
    let atributo = if locais { "f_locals" } else { "f_globals" };
    let Ok(capturado) = ligado.getattr(atributo) else {
        return Vec::new();
    };
    let Ok(pares) = capturado.call_method0("items") else {
        return Vec::new();
    };
    let Ok(iterador) = PyIterator::from_object(&pares) else {
        return Vec::new();
    };
    let mut itens = Vec::new();
    for par in iterador {
        let Ok(item) = par else {
            continue;
        };
        let Ok((chave, valor)) = item.extract::<(Py<PyAny>, Py<PyAny>)>() else {
            continue;
        };
        let Ok(nome) = chave.bind(py).extract::<String>() else {
            continue;
        };
        if !locais && nome.starts_with("__") && nome.ends_with("__") {
            continue;
        }
        itens.push(Variavel {
            valor: resumir_valor(py, valor.bind(py)),
            tipo: nome_tipo(valor.bind(py)),
            nome,
        });
    }
    itens
}

fn avaliar(py: Python<'_>, quadro: &Py<PyAny>, expressao: &str) -> (String, Option<String>) {
    let ligado = quadro.bind(py);
    let (Ok(globais), Ok(locais)) = (
        ligado.getattr("f_globals"),
        ligado.getattr("f_locals"),
    ) else {
        return (String::new(), Some(String::from("quadro indisponível")));
    };
    let chamada =
        py.import("builtins")
            .and_then(|builtins| builtins.call_method1("eval", (expressao, &globais, &locais)));
    match chamada {
        Ok(valor) => (resumir_valor(py, &valor), None),
        Err(erro) => (
            String::new(),
            Some(
                erro.value(py)
                    .str()
                    .map(|texto| texto.to_string())
                    .unwrap_or_else(|_| String::from("erro na avaliação")),
            ),
        ),
    }
}

fn responder_variaveis(id: u64, quadro: usize) {
    Python::attach(|py| {
        let referencia = {
            let guarda = estado().lock().unwrap();
            guarda.quadros.get(quadro).map(|item| item.clone_ref(py))
        };
        let (locais, globais) = match referencia {
            Some(item) => (
                extrair_variaveis(py, &item, true),
                extrair_variaveis(py, &item, false),
            ),
            None => (Vec::new(), Vec::new()),
        };
        transmitir(&Evento::Variaveis { id, locais, globais });
    });
}

fn responder_avaliacao(id: u64, quadro: usize, expressao: String) {
    Python::attach(|py| {
        let referencia = {
            let guarda = estado().lock().unwrap();
            guarda.quadros.get(quadro).map(|item| item.clone_ref(py))
        };
        let (resultado, erro) = match referencia {
            Some(item) => avaliar(py, &item, &expressao),
            None => (
                String::new(),
                Some(String::from("programa não está pausado")),
            ),
        };
        transmitir(&Evento::Avaliado { id, resultado, erro });
    });
}

fn retomar(modo: Modo) {
    let mut guarda = estado().lock().unwrap();
    let profundidade = guarda.profundidade_parada;
    guarda.motor.definir(modo, profundidade);
    guarda.resumir = true;
    espera().notify_all();
}

fn tratar_comando(comando: Comando) {
    match comando {
        Comando::DefinirPontos { arquivo, linhas } => {
            let mut guarda = estado().lock().unwrap();
            guarda.pontos.definir(&arquivo, &linhas);
        }
        Comando::Continuar => retomar(Modo::Continuar),
        Comando::PassoSobre => retomar(Modo::PassoSobre),
        Comando::PassoDentro => retomar(Modo::PassoDentro),
        Comando::PassoFora => retomar(Modo::PassoFora),
        Comando::Pausar => PAUSA_PEDIDA.store(true, Ordering::SeqCst),
        Comando::Pronto => {
            let mut guarda = estado().lock().unwrap();
            guarda.pronto = true;
            espera().notify_all();
        }
        Comando::Encerrar => {
            let mut guarda = estado().lock().unwrap();
            guarda.sair = true;
            guarda.resumir = true;
            guarda.pronto = true;
            espera().notify_all();
        }
        Comando::Variaveis { id, quadro } => responder_variaveis(id, quadro),
        Comando::Avaliar { id, quadro, expressao } => responder_avaliacao(id, quadro, expressao),
    }
}

fn iniciar_leitor(fluxo: TcpStream) {
    std::thread::spawn(move || {
        let mut linhas = BufReader::new(fluxo).lines();
        while let Some(Ok(linha)) = linhas.next() {
            if linha.trim().is_empty() {
                continue;
            }
            let Ok(comando) = serde_json::from_str::<Comando>(&linha) else {
                continue;
            };
            tratar_comando(comando);
        }
        let mut guarda = estado().lock().unwrap();
        guarda.sair = true;
        guarda.resumir = true;
        guarda.pronto = true;
        espera().notify_all();
    });
}

fn aguardar_pronto() -> bool {
    let mut guarda = estado().lock().unwrap();
    let limite = Instant::now() + ESPERA_PRONTO;
    while !guarda.pronto && !guarda.sair {
        let agora = Instant::now();
        if agora >= limite {
            return false;
        }
        match espera().wait_timeout(guarda, limite - agora) {
            Ok((proximo, _)) => guarda = proximo,
            Err(_) => return false,
        }
    }
    guarda.pronto && !guarda.sair
}

fn aguardar_retomada() -> Retomada {
    let mut guarda = estado().lock().unwrap();
    loop {
        if guarda.sair {
            return Retomada::Sair;
        }
        if guarda.resumir {
            guarda.resumir = false;
            return Retomada::Seguir;
        }
        guarda = match espera().wait(guarda) {
            Ok(proximo) => proximo,
            Err(_) => return Retomada::Sair,
        };
    }
}

fn conectar(py: Python<'_>, porta: u16) -> PyResult<()> {
    let fluxo = TcpStream::connect(("127.0.0.1", porta)).map_err(|erro| {
        PyRuntimeError::new_err(format!("não consegui falar com o depurador: {}", erro))
    })?;
    fluxo.set_nonblocking(false).map_err(|erro| {
        PyRuntimeError::new_err(format!("não consegui ajustar o canal: {}", erro))
    })?;
    let leitor = fluxo.try_clone().map_err(|erro| {
        PyRuntimeError::new_err(format!("não consegui duplicar o canal: {}", erro))
    })?;
    {
        let mut guarda = estado().lock().unwrap();
        guarda.conexao = Some(fluxo);
        guarda.pronto = false;
        guarda.sair = false;
        guarda.resumir = false;
    }
    iniciar_leitor(leitor);
    transmitir(&Evento::Conectado);
    let confirmado = py.detach(aguardar_pronto);
    if !confirmado {
        return Err(PyRuntimeError::new_err(
            "o depurador não confirmou o início da sessão",
        ));
    }
    Ok(())
}

fn nome_do_arquivo(quadro: &Bound<'_, PyAny>) -> PyResult<String> {
    quadro
        .getattr("f_code")?
        .getattr("co_filename")?
        .extract::<String>()
}

fn proximo_quadro(quadro: &Bound<'_, PyAny>) -> Option<Py<PyAny>> {
    quadro
        .getattr("f_back")
        .ok()?
        .extract::<Option<Py<PyAny>>>()
        .ok()
        .flatten()
}

fn descrever_quadro(quadro: &Bound<'_, PyAny>) -> Option<(Quadro, Py<PyAny>)> {
    let codigo = quadro.getattr("f_code").ok()?;
    let nome: String = codigo.getattr("co_name").ok()?.extract().ok()?;
    let arquivo: String = codigo.getattr("co_filename").ok()?.extract().ok()?;
    let linha: usize = quadro.getattr("f_lineno").ok()?.extract().ok()?;
    Some((
        Quadro {
            nome,
            arquivo,
            linha,
        },
        quadro.clone().unbind(),
    ))
}

fn profundidade_do_quadro(py: Python<'_>, quadro: &Bound<'_, PyAny>) -> usize {
    let mut total = 0usize;
    let mut atual: Option<Py<PyAny>> = Some(quadro.clone().unbind());
    while let Some(item) = atual {
        total += 1;
        atual = proximo_quadro(item.bind(py));
    }
    total
}

fn filtrar_escopo(
    py: Python<'_>,
    quadros: Vec<Quadro>,
    objetos: Vec<Py<PyAny>>,
    prefixos: &[String],
) -> (Vec<Quadro>, Vec<Py<PyAny>>) {
    let mut info = Vec::new();
    let mut refs = Vec::new();
    for (indice, quadro) in quadros.iter().enumerate() {
        if arquivo_em_escopo(&quadro.arquivo, prefixos) {
            info.push(quadro.clone());
            refs.push(objetos[indice].clone_ref(py));
        }
    }
    if info.is_empty() {
        return (quadros, objetos);
    }
    (info, refs)
}

fn montar_parada(
    py: Python<'_>,
    quadro: &Bound<'_, PyAny>,
    motivo: &str,
    arquivo: &str,
    linha: usize,
    detalhe: Option<String>,
) -> Parada {
    let profundidade = profundidade_do_quadro(py, quadro);
    let mut info = Vec::new();
    let mut objetos = Vec::new();
    let mut atual: Option<Py<PyAny>> = Some(quadro.clone().unbind());
    while let Some(item) = atual {
        let ligado = item.bind(py);
        if let Some((registro, referencia)) = descrever_quadro(ligado) {
            info.push(registro);
            objetos.push(referencia);
        }
        atual = proximo_quadro(ligado);
    }
    let prefixos = prefixos_snapshot();
    let (quadros, refs) = filtrar_escopo(py, info, objetos, &prefixos);
    Parada {
        motivo: motivo.to_string(),
        arquivo: arquivo.to_string(),
        linha,
        detalhe,
        quadros,
        objetos: refs,
        profundidade,
    }
}

fn executar_parada(py: Python<'_>, parada: Parada) -> PyResult<bool> {
    {
        let mut guarda = estado().lock().unwrap();
        guarda.quadros = parada.objetos;
        guarda.profundidade_parada = parada.profundidade;
        guarda.resumir = false;
    }
    PAUSA_PEDIDA.store(false, Ordering::SeqCst);
    transmitir(&Evento::Parado {
        motivo: parada.motivo,
        arquivo: parada.arquivo,
        linha: parada.linha,
        quadros: parada.quadros,
        detalhe: parada.detalhe,
    });
    match py.detach(aguardar_retomada) {
        Retomada::Seguir => {
            {
                let mut guarda = estado().lock().unwrap();
                guarda.quadros.clear();
            }
            transmitir(&Evento::Continuado);
            Ok(true)
        }
        Retomada::Sair => Ok(false),
    }
}

fn ler_linha_fonte(arquivo: &str, linha: usize) -> Option<String> {
    let conteudo = std::fs::read_to_string(arquivo).ok()?;
    conteudo
        .lines()
        .nth(linha.checked_sub(1)?)
        .map(|texto| texto.to_string())
}

fn formatar_erro(py: Python<'_>, erro: &PyErr, quadros: &[Quadro]) -> String {
    let mut texto = String::from("Traceback (most recent call last):\n");
    for quadro in quadros {
        texto.push_str(&format!(
            "  File \"{}\", line {}, in {}\n",
            quadro.arquivo, quadro.linha, quadro.nome
        ));
        if let Some(linha) = ler_linha_fonte(&quadro.arquivo, quadro.linha) {
            texto.push_str(&format!("    {}\n", linha.trim()));
        }
    }
    let tipo = erro
        .value(py)
        .get_type()
        .getattr("__name__")
        .and_then(|nome| nome.extract::<String>())
        .unwrap_or_else(|_| String::from("Exception"));
    let valor = erro
        .value(py)
        .str()
        .map(|texto| texto.to_string())
        .unwrap_or_default();
    if valor.is_empty() {
        texto.push_str(&tipo);
    } else {
        texto.push_str(&format!("{}: {}", tipo, valor));
    }
    texto
}

fn codigo_do_system_exit(py: Python<'_>, erro: &PyErr) -> i32 {
    match erro.value(py).getattr("code") {
        Ok(codigo) if codigo.is_none() => 0,
        Ok(codigo) => match codigo.extract::<i32>() {
            Ok(numero) => numero,
            Err(_) => {
                if let Ok(texto) = codigo.extract::<String>() {
                    eprint!("{}", texto);
                }
                1
            }
        },
        Err(_) => 1,
    }
}

fn quadros_do_erro(py: Python<'_>, erro: &PyErr) -> (Vec<Quadro>, Vec<Py<PyAny>>, usize) {
    let mut info = Vec::new();
    let mut objetos = Vec::new();
    let mut rastro: Option<Py<PyAny>> = erro
        .value(py)
        .getattr("__traceback__")
        .ok()
        .and_then(|valor| valor.extract::<Option<Py<PyAny>>>().ok())
        .flatten();
    while let Some(item) = rastro {
        let ligado = item.bind(py);
        if let (Ok(frame), Ok(linha)) = (
            ligado.getattr("tb_frame"),
            ligado.getattr("tb_lineno").and_then(|valor| valor.extract::<usize>()),
        ) {
            if let Some((mut registro, referencia)) = descrever_quadro(&frame) {
                registro.linha = linha;
                info.push(registro);
                objetos.push(referencia);
            }
        }
        rastro = ligado
            .getattr("tb_next")
            .ok()
            .and_then(|valor| valor.extract::<Option<Py<PyAny>>>().ok())
            .flatten();
    }
    info.reverse();
    objetos.reverse();
    let profundidade = info.len();
    let prefixos = prefixos_snapshot();
    let (quadros, refs) = filtrar_escopo(py, info, objetos, &prefixos);
    (quadros, refs, profundidade)
}

fn tratar_saida(py: Python<'_>, erro: PyErr) -> i32 {
    if erro.is_instance_of::<PySystemExit>(py) {
        return codigo_do_system_exit(py, &erro);
    }
    if erro.is_instance_of::<PyKeyboardInterrupt>(py) {
        return 130;
    }
    let (quadros, objetos, profundidade) = quadros_do_erro(py, &erro);
    let detalhe = formatar_erro(py, &erro, &quadros);
    let (arquivo, linha) = quadros
        .first()
        .map(|quadro| (quadro.arquivo.clone(), quadro.linha))
        .unwrap_or_else(|| (String::new(), 0));
    let parada = Parada {
        motivo: String::from("excecao"),
        arquivo,
        linha,
        detalhe: Some(detalhe),
        quadros,
        objetos,
        profundidade,
    };
    let _ = executar_parada(py, parada);
    1
}

#[pyfunction]
#[pyo3(signature = (caminho, argumentos, porta, diretorio_runtime))]
pub fn iniciar(
    py: Python<'_>,
    caminho: String,
    argumentos: Vec<String>,
    porta: u16,
    diretorio_runtime: String,
) -> PyResult<i32> {
    let sys = py.import("sys")?;
    let mut prefixos = vec![diretorio_runtime];
    for atributo in ["prefix", "base_prefix", "exec_prefix"] {
        if let Ok(valor) = sys.getattr(atributo) {
            if let Ok(texto) = valor.extract::<String>() {
                prefixos.push(texto);
            }
        }
    }
    {
        let mut guarda = estado().lock().unwrap();
        guarda.prefixos = prefixos;
        guarda.pontos = PontosDeParada::novo();
        guarda.motor = MotorDePassos::novo();
        guarda.quadros.clear();
        guarda.profundidade_parada = 0;
        guarda.resumir = false;
        guarda.sair = false;
        guarda.pronto = false;
    }
    PAUSA_PEDIDA.store(false, Ordering::SeqCst);
    conectar(py, porta)?;

    let diretorio_alvo = Path::new(&caminho)
        .parent()
        .map(|pasta| pasta.to_string_lossy().into_owned())
        .unwrap_or_else(|| String::from("."));
    sys.getattr("path")?
        .call_method1("insert", (0, diretorio_alvo))?;
    let mut argv = vec![caminho.clone()];
    argv.extend(argumentos);
    sys.setattr("argv", argv)?;

    let builtins = py.import("builtins")?;
    let globals = PyDict::new(py);
    globals.set_item("__name__", "__main__")?;
    globals.set_item("__file__", &caminho)?;
    globals.set_item("__builtins__", &builtins)?;

    let Some(referencia) = REFERENCIA_TRACE.get() else {
        return Err(PyRuntimeError::new_err(
            "referência de rastreamento indisponível",
        ));
    };
    sys.getattr("settrace")?.call1((referencia,))?;

    let codigo = match std::fs::read_to_string(&caminho) {
        Err(erro) => {
            let mensagem = format!("não consegui ler {}: {}", caminho, erro);
            transmitir(&Evento::Erro {
                mensagem: mensagem.clone(),
            });
            return Err(PyOSError::new_err(mensagem));
        }
        Ok(fonte) => match builtins.call_method1("compile", (&fonte, &caminho, "exec")) {
            Err(erro) => {
                transmitir(&Evento::Erro {
                    mensagem: formatar_erro(py, &erro, &[]),
                });
                1
            }
            Ok(compilado) => match builtins.call_method1("exec", (&compilado, &globals)) {
                Ok(_) => 0,
                Err(erro) => tratar_saida(py, erro),
            },
        },
    };

    let _ = sys.getattr("settrace")?.call1((py.None(),));
    transmitir(&Evento::Saiu { codigo });
    Ok(codigo)
}

#[pyfunction]
pub fn trace_fn(
    py: Python<'_>,
    quadro: &Bound<'_, PyAny>,
    evento: &str,
    _argumento: Option<Bound<'_, PyAny>>,
) -> PyResult<Option<Py<PyAny>>> {
    let Some(referencia) = REFERENCIA_TRACE.get() else {
        return Ok(None);
    };
    let manter = Some(referencia.clone_ref(py));
    let Ok(arquivo) = nome_do_arquivo(quadro) else {
        return Ok(manter);
    };
    if evento == "call" {
        let prefixos = prefixos_snapshot();
        if !arquivo_em_escopo(&arquivo, &prefixos) {
            return Ok(None);
        }
        return Ok(manter);
    }
    if evento != "line" {
        return Ok(manter);
    }
    let Ok(linha) = quadro
        .getattr("f_lineno")
        .and_then(|valor| valor.extract::<usize>())
    else {
        return Ok(manter);
    };
    let pausa = PAUSA_PEDIDA.swap(false, Ordering::SeqCst);
    let batida = estado().lock().unwrap().pontos.contem(&arquivo, linha);
    let profundidade = profundidade_do_quadro(py, quadro);
    let passo = estado().lock().unwrap().motor.deve_parar(profundidade);
    let motivo = if pausa {
        Some("pausa")
    } else if batida {
        Some("breakpoint")
    } else if passo {
        Some("passo")
    } else {
        None
    };
    if let Some(motivo) = motivo {
        let parada = montar_parada(py, quadro, motivo, &arquivo, linha, None);
        if !executar_parada(py, parada)? {
            return Err(PySystemExit::new_err(0));
        }
        return Ok(manter);
    }
    Ok(manter)
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn arquivos_do_runtime_e_da_biblioteca_ficam_fora_do_escopo() {
        let prefixos = vec![
            "/app/tool-nth".to_string(),
            "/usr/lib/python3.14".to_string(),
        ];
        assert!(arquivo_em_escopo("/projeto/main.py", &prefixos));
        assert!(!arquivo_em_escopo("/app/tool-nth/target_runner.py", &prefixos));
        assert!(!arquivo_em_escopo(
            "/usr/lib/python3.14/json/__init__.py",
            &prefixos
        ));
    }

    #[test]
    fn prefixo_parecido_nao_engole_o_vizinho() {
        let prefixos = vec!["/app/venv".to_string()];
        assert!(arquivo_em_escopo("/app/venv_extra/main.py", &prefixos));
        assert!(!arquivo_em_escopo("/app/venv/lib/x.py", &prefixos));
    }

    #[test]
    fn prefixo_vazio_nunca_exclui_nada() {
        let prefixos = vec![String::new()];
        assert!(arquivo_em_escopo("/projeto/main.py", &prefixos));
    }

    #[test]
    fn truncamento_preserva_o_limite() {
        let longo = "x".repeat(500);
        let resultado = truncar(&longo, 10);
        assert_eq!(resultado.chars().count(), 11);
        assert!(resultado.ends_with('…'));
        assert_eq!(truncar("curto", 10), "curto");
    }

    #[test]
    fn estado_comeca_parado_e_livre() {
        let guarda = estado().lock().unwrap();
        assert!(guarda.quadros.is_empty());
        assert!(!guarda.resumir);
        assert!(!guarda.sair);
        assert!(!guarda.pronto);
        assert!(!guarda.motor.deve_parar(3));
        assert!(guarda.prefixos.is_empty());
    }
}
