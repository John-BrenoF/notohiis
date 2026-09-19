import os
import shutil
from typing import List, Dict


class FileManager:
    """Funções para navegação e manipulação no sistema de arquivos."""

    @staticmethod
    def list_directory(path: str) -> List[Dict[str, str]]:
        """Lista arquivos e pastas em um diretório para o Sidebar.
        
        Retorna lista ordenada: pastas primeiro, depois arquivos, ambos em ordem alfabética.
        """
        if not path or not os.path.exists(path):
            return []
        items = []
        try:
            for entry in os.scandir(path):
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir()
                })
        except PermissionError:
            print(f"[FileManager] Sem permissão para listar: {path}")
        except OSError as e:
            print(f"[FileManager] Erro ao listar '{path}': {e}")
        return sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))

    @staticmethod
    def create_file(path: str) -> bool:
        """Cria um arquivo vazio no caminho especificado."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                pass
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao criar arquivo '{path}': {e}")
            return False

    @staticmethod
    def create_directory(path: str) -> bool:
        """Cria um diretório (e pais intermediários) no caminho especificado."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao criar diretório '{path}': {e}")
            return False

    @staticmethod
    def rename_path(old_path: str, new_name: str) -> bool:
        """Renomeia um arquivo ou diretório."""
        try:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            os.rename(old_path, new_path)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao renomear '{old_path}' para '{new_name}': {e}")
            return False

    @staticmethod
    def delete_path(path: str) -> bool:
        """Exclui um arquivo ou diretório (recursivamente)."""
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao excluir '{path}': {e}")
            return False
