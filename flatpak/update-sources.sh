#!/usr/bin/env bash

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GEN="$RAIZ/flatpak/.gen"
FBT="$GEN/flatpak-builder-tools"
VENV="$GEN/venv"

cd "$RAIZ"

echo "[1/3] Preparando geradores (flatpak-builder-tools)..."
[ -d "$FBT" ] || git clone --depth 1 https://github.com/flatpak/flatpak-builder-tools "$FBT"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" -q install --upgrade pip
"$VENV/bin/pip" -q install tomlkit aiohttp PyYAML requirements-parser packaging
[ -x "$VENV/bin/pip3" ] || ln -sf pip "$VENV/bin/pip3"

echo "[2/3] Crates Rust..."
"$VENV/bin/python" "$FBT/cargo/flatpak-cargo-generator.py" \
    core/native/Cargo.lock -o flatpak/cargo-sources-core.json
"$VENV/bin/python" "$FBT/cargo/flatpak-cargo-generator.py" \
    core/core_plugin/tool-nth/native/Cargo.lock -o flatpak/cargo-sources-tool-nth.json

echo "[3/3] Wheels Python (alvo: CPython 3.13 / x86_64)..."
PATH="$VENV/bin:$PATH" "$VENV/bin/python" "$FBT/pip/flatpak-pip-generator.py" \
    -r flatpak/requirements.txt \
    --runtime org.freedesktop.Sdk//25.08 \
    --prefer-wheels Pillow,opencv-python,numpy,lxml \
    --wheel-arches x86_64 \
    -o flatpak/python3-requirements.json

echo "[OK] Fontes regeneradas em flatpak/*.json"
