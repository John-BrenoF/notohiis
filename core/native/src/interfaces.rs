use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

#[pyclass(subclass, dict)]
pub struct TextEditor;

#[pyclass(subclass, dict)]
pub struct StatusBar;

#[pyclass(subclass, dict)]
pub struct Sidebar;

#[pyclass(subclass, dict)]
pub struct AppWindow;

#[pymethods]
impl TextEditor {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        TextEditor
    }
}

#[pymethods]
impl StatusBar {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        StatusBar
    }
}

#[pymethods]
impl Sidebar {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        Sidebar
    }
}

#[pymethods]
impl AppWindow {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        AppWindow
    }
}

#[pyclass(frozen, get_all)]
#[derive(Clone)]
pub struct EditorEvent {
    pub char: String,
    pub keysym: String,
    pub modifiers: i64,
}

#[pymethods]
impl EditorEvent {
    #[new]
    #[pyo3(signature = (char, keysym, modifiers = 0))]
    fn new(char: String, keysym: String, modifiers: i64) -> Self {
        EditorEvent { char, keysym, modifiers }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TextEditor>()?;
    m.add_class::<StatusBar>()?;
    m.add_class::<Sidebar>()?;
    m.add_class::<AppWindow>()?;
    m.add_class::<EditorEvent>()?;
    Ok(())
}
