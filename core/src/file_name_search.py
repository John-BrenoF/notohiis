import os
import threading
from dataclasses import dataclass
from typing import Callable, List

from core.src.constants import IGNORED_DIRS, FILE_NAME_SEARCH_MAX_RESULTS, SEARCH_BATCH_SIZE


@dataclass(frozen=True)
class FileNameSearchResult:
    path: str
    name: str
    is_directory: bool


class FileNameSearchService:
    """Serviço de busca por nomes de arquivos/pastas de forma assíncrona."""

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
                    name for name in directory_names
                    if name not in IGNORED_DIRS
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
                    if len(batch) >= SEARCH_BATCH_SIZE:
                        on_result(batch)
                        batch = []
                    if len(found_results) >= FILE_NAME_SEARCH_MAX_RESULTS:
                        break

                if len(found_results) >= FILE_NAME_SEARCH_MAX_RESULTS:
                    break

        if batch:
            on_result(batch)
        on_done(len(found_results))
