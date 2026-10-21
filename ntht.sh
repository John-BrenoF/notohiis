#!/bin/bash

# Resolve o caminho absoluto
COMMAND_SCRIPT="$(dirname "$(realpath "$0")")"

# Ativa ambiente virtual
source "$COMMAND_SCRIPT/.venv/bin/activate"

export PYTHONPATH="${PYTHONPATH}:$COMMAND_SCRIPT"

if ! (cd "$COMMAND_SCRIPT" && python3 -c "import notohiis_core") >/dev/null 2>&1; then
    echo "[INFO] Core nativo não compilado — compilando..."
    if ! bash "$COMMAND_SCRIPT/core/native/build.sh"; then
        echo "[ERRO] Compile com: bash core/native/build.sh (requer Rust: https://rustup.rs)" >&2
        exit 1
    fi
fi

python3 -c "from tui.window import TuiWindow; TuiWindow().run()" "$1"
