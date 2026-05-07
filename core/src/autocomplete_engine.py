import keyword
from typing import List

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

    def get_suggestions(self, content: str, line: int, column: int) -> List[str]:
        """
        Analisa o conteúdo e retorna sugestões baseadas na posição do cursor.
        Line: 1-based, Column: 0-based index.
        """
        lines = content.splitlines()
        if not lines or line > len(lines):
            return []
            
        current_line = lines[line - 1]
        
        # Retrocede para encontrar o início do que está sendo digitado (prefixo)
        start_idx = column
        while start_idx > 0 and (current_line[start_idx-1].isalnum() or current_line[start_idx-1] == '_'):
            start_idx -= 1
            
        current_word = current_line[start_idx:column]
        if not current_word or len(current_word) < 1:
            return []
            
        return [s for s in self.suggestions_base if s.startswith(current_word) and s != current_word]