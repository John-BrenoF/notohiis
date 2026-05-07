import os
import shutil
from typing import List, Dict, Optional

class FileManager:
    """Funções para navegação no sistema de arquivos."""

    @staticmethod
    def list_directory(path: str) -> List[Dict[str, str]]:
        """Lista arquivos e pastas em um diretório para o Sidebar."""
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
            pass
        return sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))

    @staticmethod
    def create_file(path: str) -> bool:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                pass
            return True
        except Exception:
            return False

    @staticmethod
    def create_directory(path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_path(path: str) -> bool:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        except Exception:
            return False