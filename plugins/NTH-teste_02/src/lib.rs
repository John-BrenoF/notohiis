use pyo3::prelude::*;

#[pyfunction]
fn setup(ctx: Bound<'_, PyAny>) -> PyResult<()> {
    println!("[BLOCO] NTH-teste_02 (Rust) carregado");
    let externos = ctx.getattr("external_plugins")?;
    externos.call_method1("append", ("bloco_rust_demo",))?;
    Ok(())
}

#[pymodule]
fn nth_teste_02(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(setup, m)?)?;
    Ok(())
}
