#!/usr/bin/env bash

set -euo pipefail
trap 'rc=$?; deactivate 2>/dev/null || true; exit "$rc"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

VENV_DIR="$SCRIPT_DIR/.venv"
PY_PKGS=(customtkinter markdown2 Pillow svglib reportlab opencv-python pyte)

INSTALL_ALIAS=false
SKIP_PIP=false
FORCE_VENV=false

usage(){
    cat <<EOF
Uso: $(basename "$0") [--install-alias] [--skip-deps] [--force] [--help] [-- args]

Opções:
  --install-alias   Instala o alias 'nth' em ~/.bashrc e/ou ~/.zshrc
  --skip-deps       Pula a instalação/sincronização de pacotes Python
  --force           Recria o ambiente virtual mesmo que exista
  --help            Mostra esta ajuda
EOF
}

while [[ ${1:-} != "" ]]; do
    case "$1" in
        --install-alias) INSTALL_ALIAS=true; shift;;
        --skip-deps) SKIP_PIP=true; shift;;
        --force) FORCE_VENV=true; shift;;
        --help|-h) usage; exit 0;;
        --) shift; break;;
        -*) echo "Opção desconhecida: $1"; usage; exit 1;;
        *) break;;
    esac
done

if command -v python3 >/dev/null 2>&1; then
    PYTHON_EXEC=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXEC=python
else
    echo "[ERRO] Nenhum interpretador Python encontrado. Instale Python 3." >&2
    exit 1
fi

echo "[INFO] Usando $PYTHON_EXEC"

if [ "$FORCE_VENV" = true ] && [ -d "$VENV_DIR" ]; then
    echo "[INFO] --force ativo: removendo venv existente..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Criando ambiente virtual em $VENV_DIR..."
    if "$PYTHON_EXEC" -m venv "$VENV_DIR"; then
        echo "[OK] Ambiente virtual criado com sucesso!"
    else
        echo "[ERRO] Falha ao criar venv."
        exit 1
    fi
else
    echo "[OK] Ambiente virtual já existe!"
fi

source "$VENV_DIR/bin/activate"

PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

if [ "$SKIP_PIP" = false ]; then
    echo "[INFO] Atualizando pip..."
    if "$PIP_BIN" install --upgrade pip --quiet; then
        echo "[OK] pip atualizado com sucesso!"
    else
        echo "[AVISO] Não foi possível atualizar o pip. Continuando..."
    fi

    echo "[INFO] Instalando dependências Python..."
    FAILED_PKGS=()
    for pkg in "${PY_PKGS[@]}"; do
        echo "[INFO] Instalando $pkg..."
        if "$PIP_BIN" install "$pkg" --upgrade --quiet; then
            echo "[OK] $pkg instalado com sucesso!"
        else
            echo "[AVISO] Falha ao instalar $pkg." >&2
            FAILED_PKGS+=("$pkg")
        fi
    done

    if [ "${#FAILED_PKGS[@]}" -gt 0 ]; then
        echo "[AVISO] Falha ao instalar as seguintes dependências: ${FAILED_PKGS[*]}" >&2
        echo "[DICA] Algumas libs (ex: tkinter, opencv) podem requerer pacotes do sistema (apt/pacman/dnf/brew)." >&2
        if command -v apt >/dev/null 2>&1; then
            echo "[SUGESTÃO] Ubuntu/Debian: sudo apt install python3-tk python3-dev libjpeg-dev libpng-dev" >&2
        elif command -v pacman >/dev/null 2>&1; then
            echo "[SUGESTÃO] Arch/CachyOS: sudo pacman -Syu tk python-pillow opencv" >&2
        elif command -v dnf >/dev/null 2>&1; then
            echo "[SUGESTÃO] Fedora: sudo dnf install python3-tkinter python3-devel" >&2
        fi
    fi
else
    echo "[INFO] Pulando instalação de dependências Python (--skip-deps)."
fi

install_alias(){
    local cmd_script="$SCRIPT_DIR/command.sh"
    if [ -f "$cmd_script" ]; then
        chmod +x "$cmd_script" || true
        local updated=false
        for cfg in "$HOME/.bashrc" "$HOME/.zshrc"; do
            if [ -f "$cfg" ] && ! grep -q "alias nth=" "$cfg"; then
                printf "\n# Notohiis Alias\nalias nth='bash %s'\n" "$cmd_script" >> "$cfg"
                echo "[OK] Alias 'nth' adicionado em $cfg com sucesso!"
                updated=true
            fi
        done
        if [ "$updated" = false ]; then
            echo "[INFO] Alias já presente ou nenhum arquivo de shell encontrado.";
        else
            echo "[DICA] Para usar agora: source ~/.bashrc (ou ~/.zshrc se usar Zsh)"
        fi
    else
        echo "[ERRO] comando $cmd_script não encontrado. Não foi possível instalar alias." >&2
    fi
}

if [ "$INSTALL_ALIAS" = true ]; then
    install_alias
fi

export PYTHONPATH="${PYTHONPATH:-}:$SCRIPT_DIR"

cd "$SCRIPT_DIR"

echo "[SUCCESS] Ambiente pronto. Iniciando Notohiis..."

if [ -f "$SCRIPT_DIR/ui/welcome_dev!.py" ]; then
    "$PYTHON_BIN" "$SCRIPT_DIR/ui/welcome_dev!.py" "$@" || echo "[AVISO] welcome_dev falhou, prosseguindo..."
fi

if [ -f "$SCRIPT_DIR/main.py" ]; then
    exec "$PYTHON_BIN" "$SCRIPT_DIR/main.py" "$@"
else
    echo "[ERRO] main.py não encontrado em $SCRIPT_DIR" >&2
    exit 1
fi