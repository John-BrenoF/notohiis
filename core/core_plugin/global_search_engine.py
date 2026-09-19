#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import os
import threading
from dataclasses import dataclass
from typing import List, Callable

from core.src.constants import (
    BINARY_EXTENSIONS, IGNORED_DIRS,
    GLOBAL_SEARCH_MAX_MATCHES, SEARCH_BATCH_SIZE,
)


@dataclass
class SearchMatch:
    file_path: str
    line_number: int
    line_text: str


class GlobalSearchEngine:
    """Motor de busca global assíncrono com cancelamento."""

    def __init__(self):
        self._cancel_event = threading.Event()
        self._search_lock = threading.Lock()

    def search_async(
        self,
        term: str,
        project_root: str,
        on_result: Callable[[List[SearchMatch]], None],
        on_done: Callable[[int, bool], None],
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
        on_done: Callable[[int, bool], None]
    ):
        if not term or not project_root or not os.path.isdir(project_root):
            on_result([])
            on_done(0, False)
            return

        compare_term = term if case_sensitive else term.lower()
        term_len = len(compare_term)
        batch: List[SearchMatch] = []
        total = 0
        hit_limit = False

        for dirpath, dirnames, filenames in os.walk(project_root):
            if self._cancel_event.is_set():
                return

            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

            for filename in filenames:
                if self._cancel_event.is_set():
                    return

                if total >= GLOBAL_SEARCH_MAX_MATCHES:
                    hit_limit = True
                    break

                file_path = os.path.join(dirpath, filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext in BINARY_EXTENSIONS:
                    continue

                file_size = self._fast_size_check(file_path)
                if file_size == 0 or file_size > 5_000_000:
                    continue

                file_matches = self._search_in_file(file_path, compare_term, term_len, case_sensitive)
                if file_matches:
                    batch.extend(file_matches)
                    total += len(file_matches)

                    if len(batch) >= SEARCH_BATCH_SIZE:
                        on_result(batch)
                        batch = []

            if hit_limit:
                break

        if batch:
            on_result(batch)

        on_done(total, hit_limit)

    def _fast_size_check(self, file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def _search_in_file(self, file_path: str, compare_term: str, term_len: int, case_sensitive: bool) -> List[SearchMatch]:
        matches: List[SearchMatch] = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, start=1):
                    if self._cancel_event.is_set():
                        return matches

                    if len(line) < term_len:
                        continue

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
