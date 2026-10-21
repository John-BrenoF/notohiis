#!/usr/bin/env bash
#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

# Compila o core nativo do Notohiis (extensão CPython em Rust) e confirma que
# `import notohiis_core` funciona. Uso: bash core/native/build.sh [cargo args]

set -euo pipefail

NATIVE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(dirname "$(dirname "$NATIVE_DIR")")"

if ! command -v cargo >/dev/null 2>&1; then
    echo "[ERRO] cargo não encontrado. Instale o Rust (https://rustup.rs)." >&2
    exit 1
fi

echo "[INFO] Compilando o core nativo (release)..."
(cd "$NATIVE_DIR" && cargo build --release "$@")

ARTEFATO="$NATIVE_DIR/target/release/libnotohiis_core.so"
LINK="$RAIZ/notohiis_core.abi3.so"
if [ -f "$ARTEFATO" ]; then
    if ln -sfn "core/native/target/release/libnotohiis_core.so" "$LINK" 2>/dev/null; then
        echo "[OK] Link criado: notohiis_core.abi3.so -> core/native/target/release/libnotohiis_core.so"
    else
        cp -f "$ARTEFATO" "$LINK"
        echo "[OK] Artefato copiado para: notohiis_core.abi3.so"
    fi
else
    echo "[AVISO] Artefato não encontrado em $ARTEFATO." >&2
fi

PYTHON_BIN="$RAIZ/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

echo "[INFO] Verificando o carregamento com $PYTHON_BIN..."
(cd "$RAIZ" && "$PYTHON_BIN" - <<'PYCORE'
import notohiis_core
print("[OK] Core nativo ativo em", notohiis_core.__file__)
PYCORE
)

echo "[OK] Pronto: o editor roda com o core em Rust."
