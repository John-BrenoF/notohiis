from core.src.app_context import AppContext

class AutoClosePlugin:
    """
    Plugin aprimorado para auto-fechamento de caracteres (brackets e quotes).
    Inclui suporte a backspace inteligente e detecção de contexto.
    """
    def __init__(self, ctx):
        self.ctx = ctx
        self.pairs = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'"
        }
        self.closers = set(self.pairs.values())
        self._bind_events()

    def _bind_events(self):
        if not self.ctx.editor:
            return
        
        # Usa a abstração do editor para bindar teclas
        self.ctx.editor.bind_key("<KeyPress>", self.handle_keypress)
        self.ctx.editor.bind_key("<BackSpace>", self.handle_backspace)

    def handle_backspace(self, event):
        """Se apagar o caractere de abertura e o de fechamento estiver logo à frente, apaga ambos."""
        editor = self.ctx.editor
        if editor.get_selection_range():
            return

        cursor = editor.get_cursor_index()
        # Verifica se o cursor está entre um par: (|)
        char_before = editor.get_char_at(editor.index_offset(cursor, -1))
        char_after = editor.get_char_at(cursor)

        if char_before in self.pairs and self.pairs[char_before] == char_after:
            editor.delete(editor.index_offset(cursor, -1), editor.index_offset(cursor, 1))
            return "break"

    def handle_keypress(self, event):
        char = event.char
        editor = self.ctx.editor
        cursor = editor.get_cursor_index()
        
        if not char:
            return

        # 1. Lógica de Envolver Seleção: Se houver texto selecionado, envolve-o
        if char in self.pairs:
            sel = editor.get_selection_range()
            if sel:
                start, end = sel
                selected_text = editor.get_text(start, end)
                
                editor.delete(start, end)
                editor.insert(f"{char}{selected_text}{self.pairs[char]}", start)
                
                # Opcional: Re-selecionar o texto (precisa de abstração tag_add se quiser ser rigoroso)
                return "break" # Impede que o caractere seja digitado novamente pelo sistema

        # 2. Lógica de "Pular": Se digitar o fechamento e ele já estiver lá, apenas move o cursor
        if char in self.closers:
            next_char = editor.get_char_at(cursor)
            if next_char == char:
                editor.set_cursor(editor.index_offset(cursor, 1))
                return "break"

        # 3. Lógica de Auto-fechamento Inteligente
        if char in self.pairs:
            # Evita auto-fechar se houver um caractere alfanumérico logo à frente
            next_char = editor.get_char_at(cursor)
            if next_char and next_char.isalnum():
                return

            editor.insert(char + self.pairs[char], cursor)
            editor.set_cursor(editor.index_offset(cursor, 1))
            # No Tkinter, insert move o cursor. Ajustamos para ficar no meio.
            editor.set_cursor(editor.index_offset(editor.get_cursor_index(), -1))

            return "break"

    def run(self):
        """Método necessário para compatibilidade com o despachante de plugins do EditorArea."""
        pass

def setup(ctx):
    """Ponto de entrada chamado pelo carregador dinâmico no main.py."""
    plugin = AutoClosePlugin(ctx)
    ctx.external_plugins.append(plugin)