import re
import hashlib
from typing import List, Tuple, Optional
import bisect
from core.src.app_context import AppContext


class PythonSyntaxPlugin:
    """Plugin para realce de sintaxe Python utilizando Tkinter tags."""

    # Cada regra é (regex, [(indice_do_grupo, tag), ...]).
    # A ORDEM IMPORTA: regras mais acima têm prioridade e "reservam" o trecho de
    # texto que casarem, impedindo que regras posteriores (ex: keyword/number)
    # coloram indevidamente conteúdo que já esteja dentro de uma string/comentário.
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
        self.ctx = AppContext()
        # Pré-compila as regras uma única vez (antes eram recompiladas a cada highlight())
        self.rules = [(re.compile(pattern), groups) for pattern, groups in self._RAW_RULES]
        # Cache simples: evita retrabalho se o conteúdo/arquivo não mudaram desde a última chamada
        self._last_hash: Optional[str] = None
        self._last_file: Optional[str] = None

    def setup_tags(self, editor: "TextEditor"):
        """Configura as cores das tags usando a abstração do editor."""
        colors = self.ctx.theme.get("syntax", {})
        for tag, color in colors.items():
            editor.configure_tag(tag, foreground=color)

    def invalidate_cache(self):
        self._last_hash = None

    def highlight(self):
        if not self.ctx.current_file or not self.ctx.current_file.endswith(".py"):
            return
        if not self.ctx.editor:
            return

        content = self.ctx.editor.get_text()

        content_hash = hashlib.md5(content.encode("utf-8", errors="ignore")).hexdigest()
        if content_hash == self._last_hash and self.ctx.current_file == self._last_file:
            return

        colors = self.ctx.theme.get("syntax", {})


        for tag in colors.keys():
            self.ctx.editor.remove_tag(tag, "1.0", "end")
        line_starts = [0]
        for m in re.finditer(r"\n", content):
            line_starts.append(m.end())

        def get_tk_index(offset: int) -> str:
            line_idx = bisect.bisect_right(line_starts, offset) - 1
            col = offset - line_starts[line_idx]
            return f"{line_idx + 1}.{col}"

        claimed_starts: List[int] = []
        claimed_ends: List[int] = []

        def is_claimed(start: int, end: int) -> bool:
            idx = bisect.bisect_right(claimed_starts, start) - 1
            if idx >= 0 and claimed_ends[idx] > start:
                return True
            idx += 1
            return idx < len(claimed_starts) and claimed_starts[idx] < end

        def claim(start: int, end: int) -> None:
            idx = bisect.bisect_right(claimed_starts, start)
            claimed_starts.insert(idx, start)
            claimed_ends.insert(idx, end)

        for pattern, group_tags in self.rules:
            for match in pattern.finditer(content):
                whole_start, whole_end = match.start(0), match.end(0)
                if is_claimed(whole_start, whole_end):
                    continue
                for group_idx, tag in group_tags:
                    if tag not in colors:
                        continue
                    g_start, g_end = match.start(group_idx), match.end(group_idx)
                    if g_start == -1:
                        continue
                    try:
                        start_idx = get_tk_index(g_start)
                        end_idx = get_tk_index(g_end)
                        self.ctx.editor.apply_tag(tag, start_idx, end_idx)
                    except Exception:
                        continue
                claim(whole_start, whole_end)

        self._last_hash = content_hash
        self._last_file = self.ctx.current_file