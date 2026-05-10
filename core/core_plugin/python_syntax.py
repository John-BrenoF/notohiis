import re
from typing import Dict
import bisect
from core.src.app_context import AppContext

class PythonSyntaxPlugin:
    """Plugin para realce de sintaxe Python utilizando Tkinter tags."""
    
    def __init__(self):
        self.ctx = AppContext()
        self.rules = [
            (r'[frb]?\"\"\"[\s\S]*?\"\"\"|[frb]?\'\'\'[\s\S]*?\'\'\'', "string"), # Multiline/Docstrings
            (r'[frb]?\".*?\"|[frb]?\'.*?\'', "string"),
            (r'\b(False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', "keyword"),
            (r'\b(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip)\b', "builtin"),
            (r'\b(self|cls)\b', "definition"),
            (r'#.*', "comment"),
            (r'\b\d+\b', "number"),
            (r'@[a-zA-Z_]\w*', "keyword"), # Decoradores
            (r'\bdef\s+([a-zA-Z_]\w*)', "definition"),
            (r'\bclass\s+([a-zA-Z_]\w*)', "definition"),
        ]

    def setup_tags(self, editor: 'TextEditor'):
        """Configura as cores das tags usando a abstração do editor."""
        colors = self.ctx.theme.get("syntax", {})
        for tag, color in colors.items():
            editor.configure_tag(tag, foreground=color)

    def highlight(self):
        """Aplica o realce de sintaxe se o arquivo for Python."""
        if not self.ctx.current_file or not self.ctx.current_file.endswith(".py"):
            return

        if not self.ctx.editor: return
        content = self.ctx.editor.get_text()
        colors = self.ctx.theme.get("syntax", {})
        
        # Limpa tags existentes antes de re-aplicar
        for tag in colors.keys():
            self.ctx.editor.remove_tag(tag, "1.0", "end")

        # Otimização: pré-calcula offsets de início de linha para busca binária
        line_starts = [0]
        for m in re.finditer(r'\n', content):
            line_starts.append(m.end())

        def get_tk_index(offset):
            """Converte offset de caractere para 'linha.coluna' de forma eficiente."""
            line_idx = bisect.bisect_right(line_starts, offset) - 1
            col = offset - line_starts[line_idx]
            return f"{line_idx + 1}.{col}"

        for pattern, tag in self.rules:
            for match in re.finditer(pattern, content):
                # Se a regra possui um grupo de captura (ex: em def/class), destacamos apenas ele
                target_group = 1 if match.groups() else 0
                try:
                    start = get_tk_index(match.start(target_group))
                    end = get_tk_index(match.end(target_group))
                    self.ctx.editor.apply_tag(tag, start, end)
                except (IndexError, Exception):
                    continue