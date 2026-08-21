import re
import hashlib
from typing import List, Tuple, Optional, Set
import bisect
from core.src.app_context import AppContext


class PythonSyntaxLexer:
    _RAW_RULES: List[Tuple[str, List[Tuple[int, str]]]] = [
        (
            # Multiline/docstrings e strings de uma linha, já respeitando aspas escapadas (\")
            r'[frbFRB]{0,2}("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\''
            r'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')',
            [(0, "string")],
        ),
        (r'#.*', [(0, "comment")]),
        (
            # "def nome" / "class Nome": destaca a keyword e o identificador em um único match
            r'\b(def|class)\b(\s+)([a-zA-Z_]\w*)',
            [(1, "keyword"), (3, "definition")],
        ),
        (r'@[a-zA-Z_]\w*', [(0, "keyword")]),
        (
            r'\b(False|None|True|and|as|assert|async|await|break|continue|del|'
            r'elif|else|except|finally|for|from|global|if|import|in|is|lambda|'
            r'nonlocal|not|or|pass|raise|return|try|while|with|yield)\b',
            [(0, "keyword")],
        ),
        (
            r'\b(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|'
            r'chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|'
            r'eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|'
            r'hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|'
            r'locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|'
            r'property|range|repr|reversed|round|set|setattr|slice|sorted|'
            r'staticmethod|str|sum|super|tuple|type|vars|zip)\b',
            [(0, "builtin")],
        ),
        (r'\b(self|cls)\b', [(0, "definition")]),
        # Aceita inteiros, floats e notação científica (melhoria sem trocar a tag)
        (r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b', [(0, "number")]),
    ]

    def __init__(self):
        # Pré-compila as regras uma única vez (antes eram recompiladas a cada highlight())
        self.compiled_rules = [(re.compile(pattern), groups) for pattern, groups in self._RAW_RULES]

    def extract_tokens(self, content_text: str, valid_syntax_tags: Set[str]) -> List[Tuple[str, int, int]]:
        syntax_tokens = []
        content_length = len(content_text)
        claimed_character_flags = bytearray(content_length)

        for compiled_pattern, group_tag_mappings in self.compiled_rules:
            for regex_match in compiled_pattern.finditer(content_text):
                match_start_offset, match_end_offset = regex_match.start(0), regex_match.end(0)

                if b'\x01' in claimed_character_flags[match_start_offset:match_end_offset]:
                    continue

                for target_group_index, target_tag_name in group_tag_mappings:
                    if target_tag_name not in valid_syntax_tags:
                        continue

                    group_start_offset, group_end_offset = regex_match.start(target_group_index), regex_match.end(target_group_index)
                    if group_start_offset == -1:
                        continue

                    syntax_tokens.append((target_tag_name, group_start_offset, group_end_offset))

                claimed_character_flags[match_start_offset:match_end_offset] = b'\x01' * (match_end_offset - match_start_offset)

        return syntax_tokens


class PythonSyntaxPlugin:
    """Plugin para realce de sintaxe Python utilizando Tkinter tags."""

    def __init__(self):
        self.application_context = AppContext()
        self.syntax_lexer = PythonSyntaxLexer()
        # Cache simples: evita retrabalho se o conteúdo/arquivo não mudaram desde a última chamada
        self._last_content_hash: Optional[str] = None
        self._last_file_path: Optional[str] = None

    def setup_tags(self, target_editor: "TextEditor"):
        """Configura as cores das tags usando a abstração do editor."""
        theme_syntax_colors = self.application_context.theme.get("syntax", {})
        for syntax_tag_name, hex_color_value in theme_syntax_colors.items():
            target_editor.configure_tag(syntax_tag_name, foreground=hex_color_value)

    def invalidate_cache(self):
        self._last_content_hash = None

    def _calculate_line_start_indices(self, content_text: str) -> List[int]:
        line_start_indices = [0]
        for newline_match in re.finditer(r"\n", content_text):
            line_start_indices.append(newline_match.end())
        return line_start_indices

    def _convert_offset_to_tkinter_index(self, character_offset: int, line_start_indices: List[int]) -> str:
        line_index = bisect.bisect_right(line_start_indices, character_offset) - 1
        column_index = character_offset - line_start_indices[line_index]
        return f"{line_index + 1}.{column_index}"

    def highlight(self):
        if not self.application_context.current_file or not self.application_context.current_file.endswith(".py"):
            return
        if not self.application_context.editor:
            return

        current_content_text = self.application_context.editor.get_text()

        current_content_hash = hashlib.md5(current_content_text.encode("utf-8", errors="ignore")).hexdigest()
        if current_content_hash == self._last_content_hash and self.application_context.current_file == self._last_file_path:
            return

        theme_syntax_colors = self.application_context.theme.get("syntax", {})
        valid_syntax_tags = set(theme_syntax_colors.keys())

        for syntax_tag_name in valid_syntax_tags:
            self.application_context.editor.remove_tag(syntax_tag_name, "1.0", "end")

        line_start_indices = self._calculate_line_start_indices(current_content_text)
        syntax_tokens = self.syntax_lexer.extract_tokens(current_content_text, valid_syntax_tags)

        for token_tag_name, token_start_offset, token_end_offset in syntax_tokens:
            try:
                start_tkinter_index = self._convert_offset_to_tkinter_index(token_start_offset, line_start_indices)
                end_tkinter_index = self._convert_offset_to_tkinter_index(token_end_offset, line_start_indices)
                self.application_context.editor.apply_tag(token_tag_name, start_tkinter_index, end_tkinter_index)
            except Exception:
                continue

        self._last_content_hash = current_content_hash
        self._last_file_path = self.application_context.current_file