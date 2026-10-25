mod adapter;
mod breakpoints;
mod debuggee;
mod protocol;
mod step_engine;

use pyo3::prelude::*;

#[pymodule]
fn tool_nth(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<adapter::SessaoDeDepuracao>()?;
    m.add_function(wrap_pyfunction!(breakpoints::linhas_executaveis, m)?)?;
    m.add_function(wrap_pyfunction!(debuggee::iniciar, m)?)?;
    m.add_function(wrap_pyfunction!(debuggee::trace_fn, m)?)?;
    debuggee::guardar_referencia_trace(m.getattr("trace_fn")?.unbind());
    Ok(())
}
