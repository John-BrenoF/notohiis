set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$TOOL_DIR/../../.." && pwd)"
NATIVE_DIR="$TOOL_DIR/native"

if ! command -v cargo >/dev/null 2>&1; then
    echo "[ERRO] cargo não encontrado. Instale o Rust (https://rustup.rs)." >&2
    exit 1
fi

echo "[INFO] Compilando o depurador (release)..."
(cd "$NATIVE_DIR" && cargo build --release "$@")

ARTEFATO="$NATIVE_DIR/target/release/libtool_nth.so"
LINK="$TOOL_DIR/tool_nth.abi3.so"
if [ -f "$ARTEFATO" ]; then
    if ln -sfn "native/target/release/libtool_nth.so" "$LINK" 2>/dev/null; then
        echo "[OK] Link criado: core/core_plugin/tool-nth/tool_nth.abi3.so"
    else
        cp -f "$ARTEFATO" "$LINK"
        echo "[OK] Artefato copiado para: core/core_plugin/tool-nth/tool_nth.abi3.so"
    fi
else
    echo "[AVISO] Artefato não encontrado em $ARTEFATO." >&2
fi

PYTHON_BIN="$RAIZ/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo "[INFO] Verificando o carregamento com $PYTHON_BIN..."
(cd "$TOOL_DIR" && "$PYTHON_BIN" -c "import tool_nth; print('[OK] Depurador ativo em', tool_nth.__file__)")

echo "[OK] Pronto: depurador compilado."
