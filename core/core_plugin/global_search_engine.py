import os
import threading
from dataclasses import dataclass
from typing import List, Callable, Optional


@dataclass
class SearchMatch:
    file_path: str
    line_number: int
    line_text: str


class GlobalSearchEngine:
    """Motor de busca global assíncrono com cancelamento."""

    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.tiff', '.svg',
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv',
        '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat'
    }

    IGNORED_DIRS = {'.git', '__pycache__', '.venv', 'node_modules', '.cache', 'cacheuser'}

    def __init__(self):
        self._cancel_event = threading.Event()
        self._search_lock = threading.Lock()

    def search_async(
        self,
        term: str,
        project_root: str,
        on_result: Callable[[List[SearchMatch]], None],
        on_done: Callable[[int], None],
        case_sensitive: bool = False
    ):
        self.cancel()
        self._cancel_event.clear()

        thread = threading.Thread(
            target=self._run_search,
            args=(term, project_root, case_sensitive, on_result, on_done),
            daemon=True
        )
        thread.start()

    def cancel(self):
        self._cancel_event.set()

    def _run_search(
        self,
        term: str,
        project_root: str,
        case_sensitive: bool,
        on_result: Callable[[List[SearchMatch]], None],
        on_done: Callable[[int], None]
    ):
        if not term or not project_root or not os.path.isdir(project_root):
            on_result([])
            on_done(0)
            return

        compare_term = term if case_sensitive else term.lower()
        batch: List[SearchMatch] = []
        total = 0
        batch_limit = 50

        for dirpath, dirnames, filenames in os.walk(project_root):
            if self._cancel_event.is_set():
                return

            dirnames[:] = [d for d in dirnames if d not in self.IGNORED_DIRS]

            for filename in filenames:
                if self._cancel_event.is_set():
                    return

                file_path = os.path.join(dirpath, filename)
                if self._is_binary(filename):
                    continue

                file_matches = self._search_in_file(file_path, compare_term, case_sensitive)
                if file_matches:
                    batch.extend(file_matches)
                    total += len(file_matches)

                    if len(batch) >= batch_limit:
                        on_result(batch)
                        batch = []

        if batch:
            on_result(batch)

        on_done(total)

    def _search_in_file(self, file_path: str, compare_term: str, case_sensitive: bool) -> List[SearchMatch]:
        matches: List[SearchMatch] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, start=1):
                    if self._cancel_event.is_set():
                        return matches
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
