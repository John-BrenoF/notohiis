import re
import tkinter as tk
from core.src.app_context import AppContext

class PythonSyntaxPlugin:
    """Plugin para realce de sintaxe Python utilizando Tkinter tags."""
    
    def __init__(self):
        self.ctx = AppContext()
        self.rules = [
            (r'\b(False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b', "keyword"),
            (r'\b(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip)\b', "builtin"),
            (r'(\".*?\"|\'.*?\')', "string"),
            (r'#.*', "comment"),
            (r'\b\d+\b', "number"),
            (r'\bdef\s+(\w+)', "definition"),
            (r'\bclass\s+(\w+)', "definition"),
        ]

    def setup_tags(self, widget: tk.Text):
        """Configura as cores das tags no widget de texto."""
        colors = self.ctx.theme.get("syntax", {})
        for tag, color in colors.items():
            widget.tag_configure(tag, foreground=color)

    def highlight(self):
        """Aplica o realce de sintaxe se o arquivo for Python."""
        if not self.ctx.current_file or not self.ctx.current_file.endswith(".py"):
            return

        editor_widget = self.ctx.editor_container.textbox._textbox
        content = editor_widget.get("1.0", tk.END)
        colors = self.ctx.theme.get("syntax", {})
        
        # Limpa tags existentes antes de re-aplicar
        for tag in colors.keys():
            editor_widget.tag_remove(tag, "1.0", tk.END)

        for pattern, tag in self.rules:
            for match in re.finditer(pattern, content):
                start = self._offset_to_index(content, match.start())
                end = self._offset_to_index(content, match.end())
                
                # Se for uma definição (def/class), colorimos apenas o nome capturado no grupo 1
                if tag == "definition":
                    # Ajusta para destacar apenas o nome da função/classe, não o 'def'
                    group_start = self._offset_to_index(content, match.start(1))
                    editor_widget.tag_add(tag, group_start, end)
                else:
                    editor_widget.tag_add(tag, start, end)

    def _offset_to_index(self, content: str, offset: int) -> str:
        """Converte offset de caractere para o formato 'linha.coluna' do Tkinter."""
        # Conta quantas quebras de linha existem até o offset
        lines = content[:offset].split('\n')
        line = len(lines)
        column = len(lines[-1])
        return f"{line}.{column}"