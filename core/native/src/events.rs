use std::collections::HashMap;
use std::sync::Mutex;

use pyo3::prelude::*;

pub const DIRTY_CHANGED: &str = "dirty_changed";
pub const THEME_CHANGED: &str = "theme_changed";
pub const FILE_CHANGED: &str = "file_changed";
pub const CONTENT_CHANGED: &str = "content_changed";
pub const LINE_NUMBERS_REDRAWN: &str = "line_numbers_redrawn";

#[pyclass]
pub struct EventBus {
    listeners: Mutex<HashMap<String, Vec<Py<PyAny>>>>,
}

impl EventBus {
    pub fn novo() -> Self {
        EventBus { listeners: Mutex::new(HashMap::new()) }
    }

    pub fn registrar(&self, event_name: &str, callback: Py<PyAny>) {
        self.listeners
            .lock()
            .unwrap()
            .entry(event_name.to_string())
            .or_default()
            .push(callback);
    }

    pub fn remover(&self, py: Python<'_>, event_name: &str, callback: Py<PyAny>) -> PyResult<()> {
        let mut listeners = self.listeners.lock().unwrap();
        if let Some(lista) = listeners.get_mut(event_name) {
            for (indice, existente) in lista.iter().enumerate() {
                if existente.bind(py).eq(callback.bind(py))? {
                    lista.remove(indice);
                    break;
                }
            }
        }
        Ok(())
    }

    pub fn emitir(
        &self,
        py: Python<'_>,
        event_name: &str,
        data: Option<Py<PyAny>>,
    ) -> PyResult<()> {
        let snapshot = {
            let listeners = self.listeners.lock().unwrap();
            listeners.get(event_name).cloned().unwrap_or_default()
        };
        let payload = data.unwrap_or_else(|| py.None());
        for callback in snapshot {
            callback.bind(py).call1((payload.clone_ref(py),))?;
        }
        Ok(())
    }
}

#[pymethods]
impl EventBus {
    #[new]
    fn new() -> Self {
        Self::novo()
    }

    fn on(&self, event_name: String, callback: Py<PyAny>) {
        self.registrar(&event_name, callback);
    }

    fn off(&self, py: Python<'_>, event_name: String, callback: Py<PyAny>) -> PyResult<()> {
        self.remover(py, &event_name, callback)
    }

    #[pyo3(signature = (event_name, data = None))]
    fn emit(&self, py: Python<'_>, event_name: String, data: Option<Py<PyAny>>) -> PyResult<()> {
        self.emitir(py, &event_name, data)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EventBus>()?;
    m.add("DIRTY_CHANGED", DIRTY_CHANGED)?;
    m.add("THEME_CHANGED", THEME_CHANGED)?;
    m.add("FILE_CHANGED", FILE_CHANGED)?;
    m.add("CONTENT_CHANGED", CONTENT_CHANGED)?;
    m.add("LINE_NUMBERS_REDRAWN", LINE_NUMBERS_REDRAWN)?;
    Ok(())
}

#[cfg(test)]
mod testes {
    use super::*;
    use pyo3::types::{PyDict, PyList};

    fn rodar(py: Python<'_>, codigo: &str) -> Py<PyDict> {
        let globals = PyDict::new(py);
        let codigo = std::ffi::CString::new(codigo).expect("código sem NUL");
        py.run(&codigo, Some(&globals), None).expect("executar código de teste");
        globals.unbind()
    }

    #[test]
    fn emit_dispara_listeners_e_off_remove() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let bus = modulo.getattr("EventBus").unwrap().call0().unwrap();

            let escopo = rodar(
                py,
                "recebidos = []\ndef ouvir(payload): recebidos.append(payload)",
            );
            let escopo = escopo.bind(py);
            let ouvir = escopo.get_item("ouvir").unwrap().unwrap();
            let recebidos = escopo.get_item("recebidos").unwrap().unwrap();

            bus.call_method1("on", ("evt", &ouvir)).unwrap();
            bus.call_method1("emit", ("evt", 42)).unwrap();
            let recebidos = recebidos.cast::<PyList>().unwrap();
            assert_eq!(recebidos.len(), 1);
            assert_eq!(recebidos.get_item(0).unwrap().extract::<i64>().unwrap(), 42);

            bus.call_method1("off", ("evt", &ouvir)).unwrap();
            bus.call_method1("emit", ("evt", 7)).unwrap();
            assert_eq!(recebidos.len(), 1);
        });
    }

    #[test]
    fn emit_sem_data_entrega_none() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let bus = modulo.getattr("EventBus").unwrap().call0().unwrap();
            let escopo = rodar(py, "vistos = []\ndef ouvir(p): vistos.append(p)");
            let vistos = escopo.bind(py).get_item("vistos").unwrap().unwrap();
            let ouvir = escopo.bind(py).get_item("ouvir").unwrap().unwrap();
            bus.call_method1("on", ("evt", ouvir)).unwrap();
            bus.call_method1("emit", ("evt",)).unwrap();
            let vistos = vistos.cast::<PyList>().unwrap();
            assert_eq!(vistos.len(), 1);
            assert!(vistos.get_item(0).unwrap().is_none());
        });
    }

    #[test]
    fn off_com_listener_desconhecido_e_inofensivo() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let bus = modulo.getattr("EventBus").unwrap().call0().unwrap();
            let escopo = rodar(py, "def outro(): pass");
            let outro = escopo.bind(py).get_item("outro").unwrap().unwrap();
            bus.call_method1("off", ("evt", outro)).unwrap();
            bus.call_method1("emit", ("evt", 1)).unwrap();
        });
    }

    #[test]
    fn constantes_de_eventos_estao_no_modulo() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let esperadas = [
                ("DIRTY_CHANGED", "dirty_changed"),
                ("THEME_CHANGED", "theme_changed"),
                ("FILE_CHANGED", "file_changed"),
                ("CONTENT_CHANGED", "content_changed"),
                ("LINE_NUMBERS_REDRAWN", "line_numbers_redrawn"),
            ];
            for (atributo, valor) in esperadas {
                let obtido: String = modulo.getattr(atributo).unwrap().extract().unwrap();
                assert_eq!(obtido, valor);
            }
        });
    }

    #[test]
    fn lista_de_listeners_fica_vazia_apos_off() {
        Python::attach(|py| {
            let modulo = PyModule::new(py, "teste").unwrap();
            register(&modulo).unwrap();
            let bus = modulo.getattr("EventBus").unwrap().call0().unwrap();
            let escopo = rodar(py, "def ouvir(p): pass");
            let ouvir = escopo.bind(py).get_item("ouvir").unwrap().unwrap();
            bus.call_method1("on", ("evt", &ouvir)).unwrap();
            bus.call_method1("off", ("evt", &ouvir)).unwrap();
            bus.call_method1("off", ("evt", &ouvir)).unwrap();
            bus.call_method1("emit", ("evt", 1)).unwrap();
        });
    }
}
