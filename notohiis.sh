#!/bin/bash

# Notohiis Editor Bootstrapper
# Este script gerencia o ambiente virtual, dependências e inicialização do sistema.

set -e # Aborta em caso de erro simples

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
pip install --upgrade pip --quiet

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
else
    # Fallback caso o requirements.txt não exista, garante o CustomTkinter
    echo "[WARN] requirements.txt não encontrado. Instalando dependência base..."
    pip install customtkinter --quiet
fi

# 5. Configuração de ambiente e execução
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "[SUCCESS] Notohiis iniciado com sucesso."
python3 main.py

# Finalização limpa
deactivate