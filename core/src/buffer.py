import os
from typing import Optional

class BufferManager:
    """Lógica de manipulação de arquivos e memória de texto."""
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """Lê o conteúdo de um arquivo de texto."""
        if not os.path.exists(file_path):
            return ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Erro ao ler arquivo: {e}")
            return ""

    @staticmethod
    def save_file(file_path: str, content: str) -> bool:
        """Salva o conteúdo no caminho especificado."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Retorna a extensão do arquivo para lógica de sintaxe futura."""
        return os.path.splitext(file_path)[1]