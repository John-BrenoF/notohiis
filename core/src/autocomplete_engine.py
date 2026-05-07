import keyword
import os
from typing import List, Optional
from core.src.lsp_client import LSPClient

class AutocompleteEngine:
    """
    Engine de autocompletar independente de interface (GUI/TUI).
    Gerencia sugestões de palavras-chave e serve como base para integração LSP.
    """
    def __init__(self):
        # Lista base de palavras-chave e built-ins do Python para fallback imediato
        self.suggestions_base = sorted(list(set(keyword.kwlist + [
            "print", "range", "len", "input", "int", "str", "list", 
            "dict", "set", "tuple", "enumerate", "zip", "open", "self", "cls",
            "append", "extend", "split", "join"
        ])))
        self.lsp = LSPClient(["pyright-langserver", "--stdio"])
        self.lsp.start()
        self.initialized = False

    def _initialize_lsp(self, project_root: str):
        if not self.initialized and project_root and self.lsp.process:
            self.lsp.send_request("initialize", {
                "rootUri": f"file://{project_root}",
                "capabilities": {
                    "textDocument": {
                        "completion": {"completionItem": {"snippetSupport": True}}
                    }
                }
            })
            self.initialized = True

    def notify_open(self, file_path: str, content: str):
        """Notifica o LSP que um arquivo foi aberto."""
        if not file_path or not self.lsp.process: return
        self.lsp.send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": f"file://{file_path}",
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })

    def request_completion(self, line: int, column: int, callback):
        """Inicia uma requisição de completação assíncrona ao LSP."""
        from core.src.app_context import AppContext
        ctx = AppContext()
        self._initialize_lsp(ctx.project_root)

        if ctx.current_file and self.lsp.process:
            def lsp_callback(resp):
                items = resp.get("result", {}).get("items", [])
                labels = [item["label"] for item in items[:15]]
                callback(labels)

            self.lsp.send_request("textDocument/completion", {
                "textDocument": {"uri": f"file://{ctx.current_file}"},
                "position": {"line": line - 1, "character": column}
            }, callback=lsp_callback)

    def get_local_fallback(self, content: str, line: int, column: int) -> List[str]:
        """Fallback rápido para palavras-chave se o LSP estiver ocupado."""
        lines = content.splitlines()
        if not lines or line > len(lines): return []
        current_line = lines[line - 1]
        start_idx = column
        while start_idx > 0 and (current_line[start_idx-1].isalnum() or current_line[start_idx-1] == '_'):
            start_idx -= 1
            
        current_word = current_line[start_idx:column]
        if not current_word:
            return []
            
        return [s for s in self.suggestions_base if s.startswith(current_word) and s != current_word]