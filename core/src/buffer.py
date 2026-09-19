import os
from typing import Optional

from core.src.constants import BINARY_EXTENSIONS


class BufferManager:
    """Lógica de manipulação de arquivos e memória de texto."""

    @staticmethod
    def read_file(file_path: str) -> str:
        """Lê o conteúdo de um arquivo de texto.
        
        Retorna string vazia para arquivos inexistentes, binários ou com erro de leitura.
        """
        if not os.path.exists(file_path):
            return ""

        ext = os.path.splitext(file_path)[1].lower()
        if ext in BINARY_EXTENSIONS:
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"[BufferManager] Erro ao ler '{file_path}': {e}")
            return ""

    @staticmethod
    def save_file(file_path: str, content: str) -> bool:
        """Salva o conteúdo no caminho especificado.
        
        Cria diretórios intermediários automaticamente.
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except (PermissionError, OSError) as e:
            print(f"[BufferManager] Erro ao salvar '{file_path}': {e}")
            return False

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Retorna a extensão do arquivo (incluindo o ponto)."""
        return os.path.splitext(file_path)[1]