import keyword
import os
from typing import List, Optional, Dict
from core.src.lsp_client import LSPClient, detect_lsp_server


class AutocompleteEngine:
    """
    Engine de autocompletar independente de interface (GUI/TUI).
    Gerencia sugestões de palavras-chave e serve como base para integração LSP.
    """
    def __init__(self):
        self.suggestions_base = sorted(list(set(keyword.kwlist + [
            "print", "range", "len", "input", "int", "str", "list",
            "dict", "set", "tuple", "enumerate", "zip", "open", "self", "cls",
            "append", "extend", "split", "join"
        ])))
        server_cmd = detect_lsp_server()
        if server_cmd:
            self.lsp = LSPClient(server_cmd)
            self.lsp.start()
        else:
            self.lsp = None
            print("[LSP] Nenhum servidor LSP encontrado. Autocompletar desativado.")
        self.initialized = False
        self._file_versions: Dict[str, int] = {}
        self._pending_initialization = False
        self._completion_seq = 0
        self._pending_open: Optional[tuple] = None

    def _normalize_uri(self, file_path: str) -> str:
        return f"file://{os.path.abspath(file_path)}"

    def _initialize_lsp(self, project_root: str):
        if self.initialized or self._pending_initialization or not project_root:
            return
        if not self.lsp or not self.lsp.is_alive():
            return

        self._pending_initialization = True

        def on_initialize_response(response):
            self.initialized = True
            self._pending_initialization = False
            self.lsp.send_notification("initialized", {})
            if self._pending_open:
                fp, _ = self._pending_open
                self._pending_open = None
                from core.src.app_context import AppContext
                ctx = AppContext()
                content = ctx.editor.get_text() if ctx.editor else ""
                self.notify_open(fp, content)

        self.lsp.send_request("initialize", {
            "rootUri": self._normalize_uri(project_root),
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": True}}
                }
            }
        }, callback=on_initialize_response)

    def has_opened(self, file_path: str) -> bool:
        return file_path in self._file_versions

    def notify_open(self, file_path: str, content: str):
        if not file_path or not self.lsp or not self.lsp.is_alive():
            return
        if not self.initialized:
            self._pending_open = (file_path, content)
            return
        self._file_versions[file_path] = 1
        self.lsp.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": self._normalize_uri(file_path),
                "languageId": "python",
                "version": self._file_versions[file_path],
                "text": content
            }
        })

    def notify_change(self, file_path: str, content: str):
        if not file_path or not self.lsp or not self.lsp.is_alive():
            return
        if not self.initialized:
            self._pending_open = (file_path, content)
            return
        if file_path not in self._file_versions:
            self.notify_open(file_path, content)
            return
        version = self._file_versions[file_path] + 1
        self._file_versions[file_path] = version
        self.lsp.send_notification("textDocument/didChange", {
            "textDocument": {
                "uri": self._normalize_uri(file_path),
                "version": version
            },
            "contentChanges": [{"text": content}]
        })

    def request_completion(self, line: int, column: int, callback):
        from core.src.app_context import AppContext
        ctx = AppContext()
        self._initialize_lsp(ctx.project_root)

        if not self.initialized or not ctx.current_file or not self.lsp or not self.lsp.is_alive():
            callback([])
            return

        if not self.has_opened(ctx.current_file):
            text = ctx.editor.get_text() if ctx.editor else ""
            self.notify_open(ctx.current_file, text)

        text = ctx.editor.get_text() if ctx.editor else ""
        lines = text.splitlines()
        if line < 1 or line > len(lines):
            callback([])
            return
        clamped_col = min(column, len(lines[line - 1]))

        self._completion_seq += 1
        current_seq = self._completion_seq

        def lsp_callback(resp):
            if current_seq != self._completion_seq:
                return
            result = resp.get("result")
            if not result:
                callback([])
                return
            
            items = result if isinstance(result, list) else result.get("items", [])
            suggestions = []
            for item in items[:15]:
                insert_text = item.get("insertText") or item.get("label")
                suggestions.append(insert_text)
            callback(suggestions)

        self.lsp.send_request("textDocument/completion", {
            "textDocument": {"uri": self._normalize_uri(ctx.current_file)},
            "position": {"line": line - 1, "character": clamped_col}
        }, callback=lsp_callback)

    def get_local_fallback(self, content: str, line: int, column: int) -> List[str]:
        lines = content.splitlines()
        if not lines or line > len(lines):
            return []
        current_line = lines[line - 1]
        start_idx = column
        while start_idx > 0 and (current_line[start_idx - 1].isalnum() or current_line[start_idx - 1] == '_'):
            start_idx -= 1
        current_word = current_line[start_idx:column]
        if not current_word:
            return []
        return [s for s in self.suggestions_base if s.startswith(current_word) and s != current_word]