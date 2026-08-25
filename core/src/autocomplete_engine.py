import keyword
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

        self.lsp.send_request("initialize", {
            "rootUri": f"file://{project_root}",
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": True}}
                }
            }
        }, callback=on_initialize_response)

    def notify_open(self, file_path: str, content: str):
        if not file_path or not self.lsp or not self.lsp.is_alive():
            return
        self._file_versions[file_path] = 1
        self.lsp.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "languageId": "python",
                "version": self._file_versions[file_path],
                "text": content
            }
        })

    def notify_change(self, file_path: str, content: str):
        if not file_path or not self.lsp or not self.lsp.is_alive():
            return
        version = self._file_versions.get(file_path, 0) + 1
        self._file_versions[file_path] = version
        self.lsp.send_notification("textDocument/didChange", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "version": version
            },
            "contentChanges": [{"text": content}]
        })

    def request_completion(self, line: int, column: int, callback):
        from core.src.app_context import AppContext
        ctx = AppContext()
        self._initialize_lsp(ctx.project_root)

        if not ctx.current_file or not self.lsp or not self.lsp.is_alive():
            return

        text = ctx.editor.get_text() if ctx.editor else ""
        lines = text.splitlines()
        if line < 1 or line > len(lines):
            callback([])
            return
        clamped_col = min(column, len(lines[line - 1]))

        def lsp_callback(resp):
            result = resp.get("result")
            if not result:
                callback([])
                return
            items = result.get("items", [])
            labels = [item["label"] for item in items[:15]]
            callback(labels)

        self.lsp.send_request("textDocument/completion", {
            "textDocument": {"uri": f"file://{ctx.current_file}"},
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
