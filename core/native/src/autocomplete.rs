use std::collections::HashSet;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::app_context::AppContext;
use crate::lsp_client::LSPClient;

const BUILTINS_SUGESTAO: &[&str] = &[
    "print", "range", "len", "input", "int", "str", "list", "dict", "set", "tuple",
    "enumerate", "zip", "open", "self", "cls", "append", "extend", "split", "join",
];

pub fn py_splitlines(texto: &str) -> Vec<&str> {
    let mut linhas = Vec::new();
    let bytes = texto.as_bytes();
    let mut inicio = 0usize;
    let mut indice = 0usize;

    while indice < bytes.len() {
        let byte = bytes[indice];
        let fim = match byte {
            b'\n' | 0x0b | 0x0c | 0x1c | 0x1d | 0x1e => {
                indice += 1;
                indice - 1
            }
            b'\r' => {
                indice += 1;
                if indice < bytes.len() && bytes[indice] == b'\n' {
                    indice += 1;
                }
                indice - if bytes[indice - 1] == b'\n' { 2 } else { 1 }
            }
            0xc2 if indice + 1 < bytes.len() && bytes[indice + 1] == 0x85 => {
                indice += 2;
                indice - 2
            }
            0xe2 if indice + 2 < bytes.len()
                && bytes[indice + 1] == 0x80
                && (bytes[indice + 2] == 0xa8 || bytes[indice + 2] == 0xa9) =>
            {
                indice += 3;
                indice - 3
            }
            _ => {
                indice += 1;
                continue;
            }
        };
        linhas.push(&texto[inicio..fim]);
        inicio = indice;
    }

    linhas.push(&texto[inicio..]);
    linhas
}

fn eh_alnum_ou_sublinhado(caractere: char) -> bool {
    caractere.is_alphanumeric() || caractere == '_'
}

#[pyclass]
struct LspCompletionCallback {
    callback: Py<PyAny>,
}

#[pymethods]
impl LspCompletionCallback {
    #[new]
    fn new(callback: Py<PyAny>) -> Self {
        LspCompletionCallback { callback }
    }

    fn __call__(&self, py: Python<'_>, resp: Py<PyAny>) -> PyResult<()> {
        let vazio = PyDict::new(py);
        let resultado = resp.call_method1(py, "get", ("result", &vazio))?;
        let itens: Vec<Py<PyAny>> = if resultado.bind(py).is_none() {
            Vec::new()
        } else {
            let lista_vazia = PyList::empty(py);
            resultado
                .call_method1(py, "get", ("items", &lista_vazia))?
                .extract(py)
                .unwrap_or_default()
        };

        let mut labels: Vec<Py<PyAny>> = Vec::new();
        for (posicao, item) in itens.iter().enumerate() {
            if posicao >= 15 {
                break;
            }
            let rotulo = match item.bind(py).get_item("label") {
                Ok(valor) => valor,
                Err(_) => match item.bind(py).getattr("label") {
                    Ok(valor) => valor,
                    Err(_) => continue,
                },
            };
            labels.push(rotulo.unbind());
        }

        self.callback.call1(py, (PyList::new(py, labels)?,))?;
        Ok(())
    }
}

#[pyclass]
pub struct AutocompleteEngine {
    suggestions_base: Vec<String>,
    lsp: Py<LSPClient>,
    initialized: bool,
}

impl AutocompleteEngine {
    fn inicializar_lsp(&self, py: Python<'_>, project_root: Option<String>) -> PyResult<()> {
        if self.initialized {
            return Ok(());
        }
        let Some(raiz) = project_root else { return Ok(()) };
        if raiz.is_empty() {
            return Ok(());
        }

        let lsp = self.lsp.borrow(py);
        if !lsp.tem_processo() {
            return Ok(());
        }

        let raizes = PyDict::new(py);
        raizes.set_item("rootUri", format!("file://{}", raiz))?;
        let capabilities = PyDict::new(py);
        let documento = PyDict::new(py);
        let completion = PyDict::new(py);
        let item = PyDict::new(py);
        item.set_item("snippetSupport", true)?;
        completion.set_item("completionItem", item)?;
        documento.set_item("completion", completion)?;
        capabilities.set_item("textDocument", documento)?;
        raizes.set_item("capabilities", capabilities)?;

        lsp.send_request(py, "initialize".to_string(), raizes.into_any().unbind(), None)?;
        Ok(())
    }
}

#[pymethods]
impl AutocompleteEngine {
    #[new]
    fn new(py: Python<'_>) -> PyResult<Self> {
        let mut sugestoes: Vec<String> = py
            .import("keyword")?
            .getattr("kwlist")?
            .extract::<Vec<String>>()?;
        sugestoes.extend(BUILTINS_SUGESTAO.iter().map(|item| item.to_string()));

        let vistas: HashSet<String> = sugestoes.into_iter().collect();
        let mut sugestoes: Vec<String> = vistas.into_iter().collect();
        sugestoes.sort();

        let lsp = Py::new(py, LSPClient::novo(vec!["jedi-language-server".to_string()]))?;
        lsp.borrow(py).start(py)?;

        Ok(AutocompleteEngine {
            suggestions_base: sugestoes,
            lsp,
            initialized: false,
        })
    }

    #[getter]
    fn lsp_cliente(&self, py: Python<'_>) -> Py<LSPClient> {
        self.lsp.clone_ref(py)
    }

    #[getter]
    fn lsp(&self, py: Python<'_>) -> Py<LSPClient> {
        self.lsp.clone_ref(py)
    }

    #[getter]
    fn suggestions_base(&self) -> Vec<String> {
        self.suggestions_base.clone()
    }

    #[getter]
    fn initialized(&self) -> bool {
        self.initialized
    }

    #[setter]
    fn set_initialized(&mut self, valor: bool) {
        self.initialized = valor;
    }

    fn _initialize_lsp(&mut self, py: Python<'_>, project_root: Option<String>) -> PyResult<()> {
        self.inicializar_lsp(py, project_root)?;
        let lsp = self.lsp.borrow(py);
        if lsp.tem_processo() {
            self.initialized = true;
        }
        Ok(())
    }

    #[pyo3(signature = (file_path, content))]
    fn notify_open(
        &self,
        py: Python<'_>,
        file_path: Option<String>,
        content: String,
    ) -> PyResult<()> {
        let Some(caminho) = file_path else { return Ok(()) };
        if caminho.is_empty() {
            return Ok(());
        }

        let lsp = self.lsp.borrow(py);
        if !lsp.tem_processo() {
            return Ok(());
        }

        let documento = PyDict::new(py);
        documento.set_item("uri", format!("file://{}", caminho))?;
        documento.set_item("languageId", "python")?;
        documento.set_item("version", 1)?;
        documento.set_item("text", content)?;

        let params = PyDict::new(py);
        params.set_item("textDocument", documento)?;
        lsp.send_notification(py, "textDocument/didOpen".to_string(), params.into_any().unbind())?;
        Ok(())
    }

    fn request_completion(
        &self,
        py: Python<'_>,
        line: i64,
        column: i64,
        callback: Py<PyAny>,
    ) -> PyResult<()> {
        let contexto = AppContext::criar_ou_obter(py)?;
        let raiz = contexto.borrow(py).slot(py, "project_root")?;
        let raiz = match raiz {
            Some(raiz) if raiz.bind(py).is_truthy()? => Some(raiz.extract::<String>(py)?),
            _ => None,
        };
        self.inicializar_lsp(py, raiz)?;

        let arquivo = contexto.borrow(py).slot(py, "current_file")?;
        let tem_arquivo = match &arquivo {
            Some(arquivo) => arquivo.bind(py).is_truthy()?,
            None => false,
        };

        let lsp = self.lsp.borrow(py);
        if tem_arquivo && lsp.tem_processo() {
            let caminho = arquivo.unwrap().extract::<String>(py)?;
            let posicao = PyDict::new(py);
            posicao.set_item("line", line - 1)?;
            posicao.set_item("character", column)?;
            let documento = PyDict::new(py);
            documento.set_item("uri", format!("file://{}", caminho))?;
            let params = PyDict::new(py);
            params.set_item("textDocument", documento)?;
            params.set_item("position", posicao)?;

            let resp_callback = Py::new(py, LspCompletionCallback { callback })?;
            lsp.send_request(
                py,
                "textDocument/completion".to_string(),
                params.into_any().unbind(),
                Some(resp_callback.into_any()),
            )?;
            return Ok(());
        }

        let editor = contexto.borrow(py).slot(py, "editor")?;
        let conteudo = match editor {
            Some(editor) if editor.bind(py).is_truthy()? => {
                editor.call_method0(py, "get_text")?.extract::<String>(py)?
            }
            _ => String::new(),
        };

        let sugestoes = self.local_fallback(&conteudo, line, column);
        let lista = PyList::new(py, sugestoes)?;
        callback.call1(py, (lista,))?;
        Ok(())
    }

    fn get_local_fallback(
        &self,
        content: String,
        line: i64,
        column: i64,
    ) -> PyResult<Vec<String>> {
        Ok(self.local_fallback(&content, line, column))
    }
}

pub fn fallback_local(base: &[String], content: &str, line: i64, column: i64) -> Vec<String> {
    let linhas = py_splitlines(content);
    if linhas.is_empty() || line > linhas.len() as i64 {
        return Vec::new();
    }

    let indice_linha = if line >= 1 {
        (line - 1) as usize
    } else {
        let abs = (-line) as usize;
        if abs > linhas.len() {
            return Vec::new();
        }
        linhas.len() - abs
    };

    let caracteres: Vec<char> = linhas[indice_linha].chars().collect();
    let coluna = (column.max(0) as usize).min(caracteres.len());
    let mut inicio = coluna;

    while inicio > 0 && eh_alnum_ou_sublinhado(caracteres[inicio - 1]) {
        inicio -= 1;
    }

    let palavra: String = caracteres[inicio..coluna].iter().collect();
    if palavra.is_empty() {
        return Vec::new();
    }

    base.iter()
        .filter(|sugestao| sugestao.starts_with(&palavra) && **sugestao != palavra)
        .cloned()
        .collect()
}

impl AutocompleteEngine {
    fn local_fallback(&self, content: &str, line: i64, column: i64) -> Vec<String> {
        fallback_local(&self.suggestions_base, content, line, column)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AutocompleteEngine>()?;
    m.add_class::<LspCompletionCallback>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn py_splitlines_espelha_o_python() {
        assert_eq!(py_splitlines("a\nb"), vec!["a", "b"]);
        assert_eq!(py_splitlines("a\r\nb"), vec!["a", "b"]);
        assert_eq!(py_splitlines("a\rb"), vec!["a", "b"]);
        assert_eq!(py_splitlines("a\n"), vec!["a", ""]);
        assert_eq!(py_splitlines(""), vec![""]);
        assert_eq!(py_splitlines("sem quebra"), vec!["sem quebra"]);
        assert_eq!(py_splitlines("a\u{2028}b"), vec!["a", "b"]); // separador de linha
        assert_eq!(py_splitlines("a\u{0085}b"), vec!["a", "b"]); // NEL
        assert_eq!(py_splitlines("a\n\nb"), vec!["a", "", "b"]);
    }

    fn sugestoes() -> Vec<String> {
        vec![
            "print".to_string(),
            "range".to_string(),
            "len".to_string(),
            "self".to_string(),
            "enumerate".to_string(),
        ]
    }

    fn fallback(conteudo: &str, line: i64, column: i64) -> Vec<String> {
        fallback_local(&sugestoes(), conteudo, line, column)
    }

    #[test]
    fn fallback_sugere_prefixo_do_cursor() {
        assert_eq!(fallback("pr", 1, 2), vec!["print".to_string()]);
        assert_eq!(
            fallback("x = ran", 1, 6),
            vec!["range".to_string()]
        );
    }

    #[test]
    fn fallback_ignora_texto_apos_o_cursor() {
        assert!(fallback("len(ab", 1, 5).is_empty());
        assert_eq!(fallback("enu|merable", 1, 3), vec!["enumerate".to_string()]);
    }

    #[test]
    fn fallback_sem_palavra_retorna_vazio() {
        assert!(fallback("", 1, 0).is_empty());
        assert!(fallback("x = 1", 1, 5).is_empty()); // coluna em "1" não é alfanumérica? é
        assert!(fallback("linha uma\nlinha duas", 3, 1).is_empty()); // linha inexistente
    }

    #[test]
    fn fallback_linha_negativa_conta_de_baixo_para_cima() {
        assert_eq!(fallback("aaa\nbbb\npr", -1, 10), vec!["print".to_string()]);
        assert_eq!(fallback("aaa\npr\nccc", -2, 4), vec!["print".to_string()]);
    }

    #[test]
    fn fallback_e_case_sensitive_como_o_python() {
        assert!(fallback("Pr", 1, 2).is_empty()); // "print" minúsculo não casa "Pr"
    }

    #[test]
    fn callback_de_completion_le_label_do_item_dicionario() {
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "vistos = []\n\
                 def cb(itens): vistos.extend(itens)\n\
                 resp = {'result': {'items': [{'label': 'print'}, {'label': 'range', 'kind': 3}]}}\n",
            );
            let escopo = escopo.bind(py);
            let cb = escopo.get_item("cb").unwrap().unwrap();
            let resp = escopo.get_item("resp").unwrap().unwrap();

            let callback =
                Py::new(py, LspCompletionCallback { callback: cb.unbind() }).unwrap();
            callback.borrow(py).__call__(py, resp.unbind()).unwrap();

            let vistos = escopo.get_item("vistos").unwrap().unwrap();
            let vistos: Vec<String> = vistos.extract().unwrap();
            assert_eq!(vistos, vec!["print".to_string(), "range".to_string()]);
        });
    }

    #[test]
    fn callback_de_completion_sem_resultado_devolve_lista_vazia() {
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "vistos = []\n\
                 def cb(itens): vistos.extend(itens)\n\
                 resp = {'result': None}\n",
            );
            let escopo = escopo.bind(py);
            let cb = escopo.get_item("cb").unwrap().unwrap();
            let resp = escopo.get_item("resp").unwrap().unwrap();

            let callback =
                Py::new(py, LspCompletionCallback { callback: cb.unbind() }).unwrap();
            callback.borrow(py).__call__(py, resp.unbind()).unwrap();

            let vistos = escopo.get_item("vistos").unwrap().unwrap();
            assert_eq!(vistos.cast::<pyo3::types::PyList>().unwrap().len(), 0);
        });
    }
}
