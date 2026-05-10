import tkinter as tk
from core.src.app_context import AppContext

class AutoClosePlugin:
    """
    Plugin que adiciona auto-fechamento para (), [], {}, "" e ''.
    Também permite envolver um texto selecionado com esses caracteres.
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
        self._bind_events()

    def _bind_events(self):
        # Obtém o editor através do contexto global
        editor = getattr(self.ctx, "editor_container", None)
        if not editor or not hasattr(editor, "textbox"):
            return
        
        # Vincula ao widget de texto interno (Tkinter puro)
        # O add="+" garante que não sobrescrevemos outros atalhos
        editor.textbox._textbox.bind("<KeyPress>", self.handle_keypress, add="+")

    def handle_keypress(self, event):
        char = event.char
        widget = event.widget
        
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

        # 2. Lógica de Auto-fechamento: Insere o par e volta o cursor
        if char in self.pairs:
            widget.insert(tk.INSERT, char + self.pairs[char])
            widget.mark_set(tk.INSERT, "insert - 1 chars")
            return "break"

        # 3. Lógica de "Pular": Se digitar o fechamento e ele já estiver lá, apenas move o cursor
        if char in [')', ']', '}', '"', "'"]:
            next_char = widget.get(tk.INSERT, f"{tk.INSERT} + 1 chars")
            if next_char == char:
                widget.mark_set(tk.INSERT, "insert + 1 chars")
                return "break"

    def run(self):
        """Método necessário para compatibilidade com o despachante de plugins do EditorArea."""
        pass

def setup(ctx):
    """Ponto de entrada chamado pelo carregador dinâmico no main.py."""
    plugin = AutoClosePlugin(ctx)
    ctx.external_plugins.append(plugin)