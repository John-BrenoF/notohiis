#!/bin/bash

# Resolve o caminho absoluto
COMMAND_SCRIPT="$(dirname "$(realpath "$0")")"

# Ativa ambiente virtual
source "$COMMAND_SCRIPT/.venv/bin/activate"

# Executa a versão TUI
export PYTHONPATH="${PYTHONPATH}:$COMMAND_SCRIPT"
python3 -c "from tui.window import TuiWindow; TuiWindow().run()"