import os
from typing import List, Dict

class FileManager:
    """Funções para navegação no sistema de arquivos."""

    @staticmethod
    def list_directory(path: str) -> List[Dict[str, str]]:
        """Lista arquivos e pastas em um diretório para o Sidebar."""
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