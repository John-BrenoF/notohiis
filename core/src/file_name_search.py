import os
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class FileNameSearchResult:
    path: str
    name: str
    is_directory: bool


class FileNameSearchService:
    IGNORED_DIRECTORIES = {
        ".git", "__pycache__", ".venv", "venv", "node_modules",
        "dist", "build", ".cache", ".pytest_cache", ".mypy_cache",
    }
    MAX_RESULTS = 1000

    def __init__(self):
        self._cancel_event = threading.Event()
        self._search_lock = threading.Lock()

    def search_async(
        self,
        query: str,
        root_path: str,
        on_result: Callable[[List[FileNameSearchResult]], None],
        on_done: Callable[[int], None],
    ) -> None:
        self.cancel()
        self._cancel_event.clear()
        search_thread = threading.Thread(
            target=self._search,
            args=(query, root_path, on_result, on_done),
            daemon=True,
        )
        search_thread.start()

    def cancel(self) -> None:
        self._cancel_event.set()

    def _search(
        self,
        query: str,
        root_path: str,
        on_result: Callable[[List[FileNameSearchResult]], None],
        on_done: Callable[[int], None],
    ) -> None:
        normalized_query = query.strip().casefold()
        if not normalized_query or not root_path or not os.path.isdir(root_path):
            on_result([])
            on_done(0)
            return

        found_results: List[FileNameSearchResult] = []
        batch: List[FileNameSearchResult] = []
        with self._search_lock:
            for directory_path, directory_names, file_names in os.walk(root_path):
                if self._cancel_event.is_set():
                    return

                directory_names[:] = [
                    directory_name
                    for directory_name in directory_names
                    if directory_name not in self.IGNORED_DIRECTORIES
                ]
                entries = [(name, True) for name in directory_names]
                entries.extend((name, False) for name in file_names)

                for entry_name, is_directory in entries:
                    if self._cancel_event.is_set():
                        return
                    if normalized_query not in entry_name.casefold():
                        continue

                    result = FileNameSearchResult(
                        path=os.path.join(directory_path, entry_name),
                        name=entry_name,
                        is_directory=is_directory,
                    )
                    found_results.append(result)
                    batch.append(result)
                    if len(batch) >= 30:
                        on_result(batch)
                        batch = []
                    if len(found_results) >= self.MAX_RESULTS:
                        break

                if len(found_results) >= self.MAX_RESULTS:
                    break

        if batch:
            on_result(batch)
        on_done(len(found_results))
