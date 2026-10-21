use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::constants;
use crate::runtime;

#[pyclass(frozen, get_all)]
pub struct FileNameSearchResult {
    pub path: String,
    pub name: String,
    pub is_directory: bool,
}

#[pymethods]
impl FileNameSearchResult {
    #[new]
    fn new(path: String, name: String, is_directory: bool) -> Self {
        FileNameSearchResult { path, name, is_directory }
    }
}

enum Fluxo {
    Seguir,
    Parar,
    Cancelado,
}

#[pyclass]
pub struct FileNameSearchService {
    cancel_event: Arc<AtomicBool>,
    search_lock: Arc<Mutex<()>>,
}

impl FileNameSearchService {
    pub fn novo() -> Self {
        FileNameSearchService {
            cancel_event: Arc::new(AtomicBool::new(false)),
            search_lock: Arc::new(Mutex::new(())),
        }
    }

    fn cancelar(&self) {
        self.cancel_event.store(true, Ordering::SeqCst);
    }

    fn executar_busca(
        &self,
        py: Python<'_>,
        query: &str,
        root_path: &str,
        on_result: &Py<PyAny>,
        on_done: &Py<PyAny>,
    ) -> PyResult<()> {
        let normalizado = runtime::casefold(query.trim());
        let raiz = Path::new(root_path);
        if normalizado.is_empty() || root_path.is_empty() || !raiz.is_dir() {
            on_result.call1(py, (PyList::empty(py),))?;
            on_done.call1(py, (0i64,))?;
            return Ok(());
        }

        let mut encontrados: Vec<Py<FileNameSearchResult>> = Vec::new();
        let mut lote: Vec<Py<FileNameSearchResult>> = Vec::new();

        {
            let _guarda = self.search_lock.lock().unwrap();
            let mut contexto = Contexto {
                cancel_event: &self.cancel_event,
                normalizado: &normalizado,
                encontrados: &mut encontrados,
                lote: &mut lote,
                on_result,
                py,
            };
            match contexto.caminhar(raiz)? {
                Fluxo::Cancelado => return Ok(()),
                Fluxo::Parar | Fluxo::Seguir => (),
            }
        }

        if !lote.is_empty() {
            let restante = std::mem::take(&mut lote);
            on_result.call1(py, (PyList::new(py, restante)?,))?;
        }
        on_done.call1(py, (encontrados.len() as i64,))?;
        Ok(())
    }
}

struct Contexto<'a> {
    cancel_event: &'a AtomicBool,
    normalizado: &'a str,
    encontrados: &'a mut Vec<Py<FileNameSearchResult>>,
    lote: &'a mut Vec<Py<FileNameSearchResult>>,
    on_result: &'a Py<PyAny>,
    py: Python<'a>,
}

impl Contexto<'_> {
    fn cancelado(&self) -> bool {
        self.cancel_event.load(Ordering::SeqCst)
    }

    fn caminhar(&mut self, diretorio: &Path) -> PyResult<Fluxo> {
        if self.cancelado() {
            return Ok(Fluxo::Cancelado);
        }

        let mut diretorios: Vec<String> = Vec::new();
        let mut arquivos: Vec<String> = Vec::new();
        let leitura = match std::fs::read_dir(diretorio) {
            Ok(leitura) => leitura,
            Err(_) => return Ok(Fluxo::Seguir),
        };
        for entrada in leitura.flatten() {
            let nome = entrada.file_name().to_string_lossy().into_owned();
            let eh_dir = std::fs::metadata(entrada.path()).map(|m| m.is_dir()).unwrap_or(false);
            if eh_dir {
                if !constants::is_ignored_dir(&nome) {
                    diretorios.push(nome);
                }
            } else {
                arquivos.push(nome);
            }
        }

        let mut entradas: Vec<(String, bool)> = Vec::with_capacity(diretorios.len() + arquivos.len());
        for nome in diretorios.iter() {
            entradas.push((nome.clone(), true));
        }
        for nome in arquivos.iter() {
            entradas.push((nome.clone(), false));
        }

        for (nome, eh_dir) in entradas {
            if self.cancelado() {
                return Ok(Fluxo::Cancelado);
            }
            if !self.normalizado.is_empty()
                && !runtime::casefold(&nome).contains(self.normalizado)
            {
                continue;
            }

            let caminho = diretorio.join(&nome).to_string_lossy().into_owned();
            let resultado = Py::new(
                self.py,
                FileNameSearchResult { path: caminho, name: nome, is_directory: eh_dir },
            )?;
            self.encontrados.push(resultado.clone_ref(self.py));
            self.lote.push(resultado);

            if self.lote.len() >= constants::SEARCH_BATCH_SIZE as usize {
                let lote = std::mem::take(self.lote);
                self.on_result
                    .call1(self.py, (PyList::new(self.py, lote)?,))?;
            }
            if self.encontrados.len() >= constants::FILE_NAME_SEARCH_MAX_RESULTS as usize {
                return Ok(Fluxo::Parar);
            }
        }

        for nome in diretorios {
            let filho = diretorio.join(&nome);
            match self.caminhar(&filho)? {
                Fluxo::Cancelado => return Ok(Fluxo::Cancelado),
                Fluxo::Parar => return Ok(Fluxo::Parar),
                Fluxo::Seguir => (),
            }
        }
        Ok(Fluxo::Seguir)
    }
}

#[pymethods]
impl FileNameSearchService {
    #[new]
    fn new() -> Self {
        Self::novo()
    }

    fn cancel(&self) {
        self.cancelar();
    }

    fn search_async(
        &self,
        query: String,
        root_path: String,
        on_result: Py<PyAny>,
        on_done: Py<PyAny>,
    ) -> PyResult<()> {
        self.cancelar();
        self.cancel_event.store(false, Ordering::SeqCst);

        let cancel_event = Arc::clone(&self.cancel_event);
        let search_lock = Arc::clone(&self.search_lock);
        thread::spawn(move || {
            Python::attach(|py| {
                let servico = FileNameSearchService { cancel_event, search_lock };
                if let Err(erro) = servico.executar_busca(py, &query, &root_path, &on_result, &on_done)
                {
                    erro.print(py);
                }
            });
        });
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FileNameSearchResult>()?;
    m.add_class::<FileNameSearchService>()?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;
    use std::fs;

    fn arvore(base: &Path) {
        fs::create_dir_all(base.join("src/modulos")).unwrap();
        fs::create_dir_all(base.join(".git")).unwrap();
        fs::create_dir_all(base.join("docs")).unwrap();
        fs::write(base.join("src/main.py"), "").unwrap();
        fs::write(base.join("src/modulos/util.py"), "").unwrap();
        fs::write(base.join("docs/leia-me.md"), "").unwrap();
        fs::write(base.join(".git/config"), "").unwrap();
    }

    fn busca_sincrona(query: &str, raiz: &str) -> (Vec<String>, Vec<String>, i64) {
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "resultados = []\n\
                 total = [0]\n\
                 def on_result(lote): resultados.extend((r.name, r.is_directory) for r in lote)\n\
                 def on_done(n): total[0] = n",
            );
            let escopo = escopo.bind(py);
            let on_result = escopo.get_item("on_result").unwrap().unwrap().unbind();
            let on_done = escopo.get_item("on_done").unwrap().unwrap().unbind();
            let servico = Py::new(py, FileNameSearchService::novo()).unwrap();
            servico
                .borrow(py)
                .executar_busca(py, query, raiz, &on_result, &on_done)
                .unwrap();
            let pares: Vec<(String, bool)> = escopo
                .get_item("resultados")
                .unwrap()
                .unwrap()
                .extract()
                .unwrap();
            let total = escopo.get_item("total").unwrap().unwrap();
            let total: i64 = total.get_item(0).unwrap().extract().unwrap();
            let mut nomes = Vec::new();
            let mut diretorios = Vec::new();
            for (nome, eh_dir) in pares {
                if eh_dir {
                    diretorios.push(nome);
                } else {
                    nomes.push(nome);
                }
            }
            (nomes, diretorios, total)
        })
    }

    #[test]
    fn busca_encontra_arquivos_e_pasta_sem_ignorados() {
        let dir = crate::teste_util::dir_temporario("fns_busca");
        arvore(&dir);
        let raiz = dir.to_string_lossy().to_string();
        let (nomes, diretorios, total) = busca_sincrona("mod", &raiz);
        assert!(diretorios.contains(&"modulos".to_string()));
        assert!(nomes.is_empty()); // .git é ignorado; nenhum arquivo casa com "mod"
        assert_eq!(total, 1);
    }

    #[test]
    fn busca_e_case_insensitive_como_no_python() {
        let dir = crate::teste_util::dir_temporario("fns_case");
        arvore(&dir);
        let raiz = dir.to_string_lossy().to_string();
        let (nomes, diretorios, total) = busca_sincrona("MAIN", &raiz);
        assert_eq!(nomes, vec!["main.py".to_string()]);
        assert!(diretorios.is_empty());
        assert_eq!(total, 1);
    }

    #[test]
    fn busca_vazia_ou_raiz_invalida_chama_callbacks_sem_resultado() {
        let (nomes, diretorios, total) = busca_sincrona("", "/qualquer");
        assert!(nomes.is_empty() && diretorios.is_empty());
        assert_eq!(total, 0);

        let dir = crate::teste_util::dir_temporario("fns_vazio");
        let (nomes, diretorios, total) = busca_sincrona("algo", &dir.to_string_lossy());
        assert!(nomes.is_empty() && diretorios.is_empty());
        assert_eq!(total, 0);

        let (nomes, diretorios, total) = busca_sincrona("algo", "/nao/existe/dir");
        assert!(nomes.is_empty() && diretorios.is_empty());
        assert_eq!(total, 0);
    }

    #[test]
    fn busca_marca_diretorios_vs_arquivos() {
        let dir = crate::teste_util::dir_temporario("fns_tipo");
        arvore(&dir);
        Python::attach(|py| {
            let escopo = crate::teste_util::rodar(
                py,
                "pares = []\ndef on_result(lote): pares.extend((r.name, r.is_directory) for r in lote)\ndef on_done(n): pass",
            );
            let escopo = escopo.bind(py);
            let on_result = escopo.get_item("on_result").unwrap().unwrap().unbind();
            let on_done = escopo.get_item("on_done").unwrap().unwrap().unbind();
            let servico = Py::new(py, FileNameSearchService::novo()).unwrap();
            servico
                .borrow(py)
                .executar_busca(py, "docs", &dir.to_string_lossy(), &on_result, &on_done)
                .unwrap();
            let pares: Vec<(String, bool)> = escopo.get_item("pares").unwrap().unwrap().extract().unwrap();
            assert_eq!(pares, vec![("docs".to_string(), true)]);
        });
    }

    #[test]
    fn resultado_python_expoe_os_tres_campos() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let resultado = modulo
                .getattr("FileNameSearchResult")
                .unwrap()
                .call1(("/a/b.py", "b.py", false))
                .unwrap();
            assert_eq!(resultado.getattr("path").unwrap().extract::<String>().unwrap(), "/a/b.py");
            assert_eq!(resultado.getattr("name").unwrap().extract::<String>().unwrap(), "b.py");
            assert!(!resultado.getattr("is_directory").unwrap().extract::<bool>().unwrap());
        });
    }

    #[test]
    fn cancel_marca_evento_e_proxima_busca_reinicia() {
        let servico = Python::attach(|py| Py::new(py, FileNameSearchService::novo()).unwrap());
        Python::attach(|py| servico.borrow(py).cancelar());
        let dir = crate::teste_util::dir_temporario("fns_cancel");
        fs::write(dir.join("arquivo.txt"), "").unwrap();
        let (nomes, _diretorios, total) = busca_sincrona("arquivo", &dir.to_string_lossy());
        assert_eq!(nomes, vec!["arquivo.txt".to_string()]);
        assert_eq!(total, 1);
    }
}
