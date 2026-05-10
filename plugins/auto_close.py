import tkinter as tk
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
        # Obtém o editor através do contexto global
        editor = getattr(self.ctx, "editor_container", None)
        if not editor or not hasattr(editor, "textbox"):
            return
        
        # Vincula ao widget de texto interno (Tkinter puro)
        # O add="+" garante que não sobrescrevemos outros atalhos
        editor.textbox._textbox.bind("<KeyPress>", self.handle_keypress, add="+")
        editor.textbox._textbox.bind("<BackSpace>", self.handle_backspace, add="+")

    def handle_backspace(self, event):
        """Se apagar o caractere de abertura e o de fechamento estiver logo à frente, apaga ambos."""
        widget = event.widget
        if widget.tag_ranges(tk.SEL):
            return

        cursor = widget.index(tk.INSERT)
        # Verifica se o cursor está entre um par: (|)
        char_before = widget.get(f"{cursor} - 1 chars", cursor)
        char_after = widget.get(cursor, f"{cursor} + 1 chars")

        if char_before in self.pairs and self.pairs[char_before] == char_after:
            widget.delete(f"{cursor} - 1 chars", f"{cursor} + 1 chars")
            return "break"

    def handle_keypress(self, event):
        char = event.char
        widget = event.widget
        cursor = widget.index(tk.INSERT)
        
        if not char:
            return

        # 1. Lógica de Envolver Seleção: Se houver texto selecionado, envolve-o
        if char in self.pairs:
            if widget.tag_ranges(tk.SEL):
                start = widget.index(tk.SEL_FIRST)
                end = widget.index(tk.SEL_LAST)
                selected_text = widget.get(start, end)
                
                widget.delete(start, end)
                widget.insert(start, f"{char}{selected_text}{self.pairs[char]}")
                
                # Mantém o texto selecionado após envolver
                new_end = widget.index(f"{start} + {len(selected_text) + 1} chars")
                widget.tag_add(tk.SEL, f"{start} + 1 chars", new_end)
                return "break" # Impede que o caractere seja digitado novamente pelo sistema

        # 2. Lógica de "Pular": Se digitar o fechamento e ele já estiver lá, apenas move o cursor
        if char in self.closers:
            next_char = widget.get(cursor, f"{cursor} + 1 chars")
            if next_char == char:
                widget.mark_set(tk.INSERT, "insert + 1 chars")
                return "break"

        # 3. Lógica de Auto-fechamento Inteligente
        if char in self.pairs:
            # Evita auto-fechar se houver um caractere alfanumérico logo à frente
            # Isso impede que o plugin atrapalhe quando estamos editando no meio de uma palavra
            next_char = widget.get(cursor, f"{cursor} + 1 chars")
            if next_char and next_char.isalnum():
                return

            widget.insert(tk.INSERT, char + self.pairs[char])
            widget.mark_set(tk.INSERT, "insert - 1 chars")
            return "break"

    def run(self):
        """Método necessário para compatibilidade com o despachante de plugins do EditorArea."""
        pass

def setup(ctx):
    """Ponto de entrada chamado pelo carregador dinâmico no main.py."""
    plugin = AutoClosePlugin(ctx)
    ctx.external_plugins.append(plugin)