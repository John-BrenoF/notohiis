from core.src.app_context import AppContext

class AutoClosePlugin:
    """
    Plugin aprimorado para auto-fechamento de caracteres (brackets e quotes).
    Inclui suporte a backspace inteligente, "pular" fechamento existente
    e detecção de contexto (evita fechar no meio de palavras).
    """

    DEFAULT_PAIRS = {
        '(': ')',
        '[': ']',
        '{': '}',
        '"': '"',
        "'": "'",
    }

    def __init__(self, ctx: AppContext, pairs: dict | None = None):
        self.ctx = ctx
        self.pairs = pairs or dict(self.DEFAULT_PAIRS)
        self.openers = set(self.pairs.keys())
        self.closers = set(self.pairs.values())
        self._bound = False
        self._bind_events()

    def _bind_events(self):
        editor = self.ctx.editor
        if not editor:
            return
        editor.bind_key("<KeyPress>", self.handle_keypress)
        editor.bind_key("<BackSpace>", self.handle_backspace)
        self._bound = True

    def teardown(self):
        """Desliga o plugin, removendo os binds (se o editor suportar unbind)."""
        editor = self.ctx.editor
        if not editor or not self._bound:
            return
        unbind = getattr(editor, "unbind_key", None)
        if callable(unbind):
            unbind("<KeyPress>", self.handle_keypress)
            unbind("<BackSpace>", self.handle_backspace)
        self._bound = False

    def _safe_char_before(self, editor, cursor):
        """Retorna o caractere anterior ao cursor, ou '' se estiver no início."""
        try:
            pos = editor.index_offset(cursor, -1)
        except (IndexError, ValueError):
            return ""
        char = editor.get_char_at(pos)
        return char or ""

    def handle_backspace(self, event):
        """Se apagar o caractere de abertura e o de fechamento estiver logo à frente, apaga ambos."""
        editor = self.ctx.editor
        if not editor or editor.get_selection_range():
            return

        cursor = editor.get_cursor_index()
        char_before = self._safe_char_before(editor, cursor)
        char_after = editor.get_char_at(cursor) or ""

        if char_before in self.pairs and self.pairs[char_before] == char_after:
            editor.delete(editor.index_offset(cursor, -1), editor.index_offset(cursor, 1))
            return "break"
        return None

    def handle_keypress(self, event):
        char = event.char
        editor = self.ctx.editor
        if not editor or not char:
            return None

        cursor = editor.get_cursor_index()

        if char in self.pairs:
            sel = editor.get_selection_range()
            if sel:
                start, end = sel
                selected_text = editor.get_text(start, end)
                editor.delete(start, end)
                editor.insert(f"{char}{selected_text}{self.pairs[char]}", start)

                reselect = getattr(editor, "set_selection_range", None)
                if callable(reselect):
                    new_start = editor.index_offset(start, 1)
                    new_end = editor.index_offset(new_start, len(selected_text))
                    reselect(new_start, new_end)
                return "break"

        if char in self.closers:
            next_char = editor.get_char_at(cursor)
            if next_char == char:
                editor.set_cursor(editor.index_offset(cursor, 1))
                return "break"

        if char in self.pairs:
            next_char = editor.get_char_at(cursor)
            char_before = self._safe_char_before(editor, cursor)

            if next_char and next_char.isalnum():
                return None

            if char in ("'", '"') and char_before.isalnum():
                return None

            insert_pos = cursor
            editor.insert(char + self.pairs[char], insert_pos)
            editor.set_cursor(editor.index_offset(insert_pos, 1))
            return "break"

        return None

    def run(self):
        pass


def setup(ctx: AppContext):
    plugin = AutoClosePlugin(ctx)
    ctx.external_plugins.append(plugin)