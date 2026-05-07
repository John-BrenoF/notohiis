#!/bin/bash

# Resolve o caminho absoluto do arquivo fornecido
if [ -n "$1" ]; then
    TARGET_FILE="$(realpath "$1")"
else
    TARGET_FILE=""
fi

# Chama o bootstrapper principal passando o arquivo como argumento
bash "$(dirname "$(realpath "$0")")/notohiis.sh" "$TARGET_FILE"