#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

"""
Constantes compartilhadas entre core e plugins.
Evita duplicação de listas de extensões e diretórios ignorados.
"""

# Extensões de arquivos binários (não devem ser carregados como texto)
BINARY_EXTENSIONS = frozenset({
    # Imagens
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.tiff', '.svg',
    # Vídeo
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv',
    # Binários compilados
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat', '.o', '.a', '.lib',
})

# Diretórios ignorados por buscas e indexação
IGNORED_DIRS = frozenset({
    '.git', '__pycache__', '.venv', 'venv', 'node_modules',
    '.cache', 'cacheuser', 'bin', '.bin', 'dist', 'build',
    '.tox', '.mypy_cache', '.pytest_cache', '.eggs',
    'site-packages', '.npm', '.yarn',
})

# Limites de busca
GLOBAL_SEARCH_MAX_MATCHES = 5000
FILE_NAME_SEARCH_MAX_RESULTS = 1000
SEARCH_BATCH_SIZE = 30
