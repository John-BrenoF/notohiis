import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchMatch:
    file_path: str
    line_number: int
    line_text: str


class GlobalSearchEngine:
    """Motor de busca global: percorre arquivos do projeto e retorna matches."""

    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.tiff', '.svg',
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv',
        '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat'
    }

    IGNORED_DIRS = {'.git', '__pycache__', '.venv', 'node_modules', '.cache', 'cacheuser'}

    def search(self, term: str, project_root: str, case_sensitive: bool = False) -> List[SearchMatch]:
        if not term or not project_root or not os.path.isdir(project_root):
            return []

        matches: List[SearchMatch] = []
        compare_term = term if case_sensitive else term.lower()

        for dirpath, dirnames, filenames in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORED_DIRS]

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if self._is_binary(filename):
                    continue

                file_matches = self._search_in_file(file_path, compare_term, case_sensitive)
                matches.extend(file_matches)

        return matches

    def count_matches(self, term: str, project_root: str, case_sensitive: bool = False) -> int:
        return len(self.search(term, project_root, case_sensitive))

    def _search_in_file(self, file_path: str, compare_term: str, case_sensitive: bool) -> List[SearchMatch]:
        matches: List[SearchMatch] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, start=1):
                    compare_line = line if case_sensitive else line.lower()
                    if compare_term in compare_line:
                        matches.append(SearchMatch(
                            file_path=file_path,
                            line_number=line_number,
                            line_text=line.rstrip('\n')
                        ))
        except (UnicodeDecodeError, PermissionError, OSError):
            pass
        return matches

    def _is_binary(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.BINARY_EXTENSIONS
