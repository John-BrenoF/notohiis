#!/bin/bash

# Notohiis Editor Bootstrapper
# Este script gerencia o ambiente virtual, dependências e inicialização do sistema.

# Calcula o diretório do projeto dinamicamente
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"

FIRST_RUN=false
set -e # Aborta em caso de erro simples



# 0. Configuração Inicial (Splash Screen e Alias)
if [ "$FIRST_RUN" = true ]; then
    show_splash
    
    # Configuração do Alias 'nth'
    COMMAND_SCRIPT="$(dirname "$(realpath "$0")")/command.sh"
    chmod +x "$COMMAND_SCRIPT" # Garante permissão de execução

    # Detecta arquivos de configuração do shell (Bash e Zsh para CachyOS/Arch)
    HAS_UPDATED=false
    for CONFIG in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [ -f "$CONFIG" ]; then
            if ! grep -q "alias nth=" "$CONFIG"; then
                echo "" >> "$CONFIG"
                echo "# Notohiis Alias" >> "$CONFIG"
                echo "alias nth='bash $COMMAND_SCRIPT'" >> "$CONFIG"
                echo "[INFO] Alias 'nth' adicionado ao $CONFIG."
                HAS_UPDATED=true
            fi
        fi
    done

    if [ "$HAS_UPDATED" = true ]; then
        echo "[DICA] O comando 'nth' foi instalado. Para usá-lo agora, execute:"
        echo "       source ~/.bashrc (ou source ~/.zshrc caso use Zsh)"
    fi

    # Sed técnico: Altera a flag para false para evitar re-exibição
    sed -i "s/^FIRST_RUN=true/FIRST_RUN=false/" "$0"
fi

# 1. Verificação de dependências do sistema
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não encontrado. Por favor, instale o Python 3 para continuar."
    exit 1
fi

# 2. Gerenciamento do Ambiente Virtual (VENV)
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Ambiente virtual não detectado. Criando em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[ERRO] Falha ao criar o ambiente virtual."
        exit 1
    fi
fi

# 3. Ativação do ambiente
source "$VENV_DIR/bin/activate"

# 4. Atualização de ferramentas e dependências
echo "[INFO] Sincronizando dependências..."

# Permitimos que a atualização falhe (ex: rede instável) para que o editor 
# possa abrir se as bibliotecas já estiverem presentes localmente.
pip install --upgrade pip --quiet || echo "[AVISO] Não foi possível atualizar o pip."

# Garante a instalação das dependências core e dos plugins (Markdown, etc)
pip install customtkinter markdown2 tkinterweb Pillow svglib reportlab opencv-python --upgrade --quiet || {
    echo "[AVISO] Falha ao sincronizar dependências. Tentando iniciar com bibliotecas locais..."
}

# 5. Configuração de ambiente e execução
cd "$SCRIPT_DIR"
export PYTHONPATH="${PYTHONPATH}:$SCRIPT_DIR"

echo "[SUCCESS] Notohiis iniciado com sucesso."
python3 "$SCRIPT_DIR/ui/welcome_dev!.py" "$1"

python3 "$SCRIPT_DIR/main.py" "$1"

# Finalização limpa
deactivate