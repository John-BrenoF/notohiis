"""Widget TUI de edição de texto — implementa o protocolo `core.interfaces.TextEditor`.

O GUI (Tk) expõe índices no formato ``"linha.coluna"`` (linha 1-based) e um
sistema de tags; o Textual usa tuplas ``(linha, coluna)`` 0-based e não tem tags.
Esta classe adapta os dois mundos para que o código compartilhado (histórico de
undo, barra de status, plugins core) funcione igual nos dois frontends.
"""

import re
from typing import Any, Callable, Dict, Optional, Tuple

from textual import events
from textual.widgets import TextArea

from core.events import FILE_CHANGED
from core.interfaces import EditorEvent, TextEditor
from core.src.app_context import AppContext

# Sintaxe Tk -> Textual: `<Control-Alt-Down>` vira `ctrl+alt+down`.
_TK_MODIFIERS = {
    "Control": "ctrl", "Ctrl": "ctrl",
    "Alt": "alt", "Shift": "shift",
    "Meta": "meta", "Command": "meta", "Cmd": "meta",
}

# Bindings genéricos (`<KeyPress>`, `<Button-1>`, ...) viram curinga.
_GENERIC_TK_EVENTS = ("KeyPress", "KeyRelease", "Button", "ButtonPress", "ButtonRelease")

_OFFSET_SUFFIX = re.compile(r"^(?P<base>.*?)\s*(?P<sign>[+-])\s*(?P<n>\d+)\s*chars?$")


class EditorArea(TextArea):
    """Widget TUI para edição de texto.

    Implementa estruturalmente o protocolo `TextEditor` (não herda dele: `Protocol`
    tem metaclass incompatível com a do `TextArea` do Textual).
    """

    def __init__(self, **kwargs):
        super().__init__(
            language="python",
            theme="vscode_dark",
            soft_wrap=False,
            show_line_numbers=True,
            id="editor",
            **kwargs
        )
        self.ctx = AppContext()
        self._key_callbacks: Dict[str, Callable[[EditorEvent], Any]] = {}

    def on_mount(self):
        self.ctx.set_editor(self)

    def on_text_area_changed(self, event) -> None:
        """Handler da mensagem ``TextArea.Changed`` do Textual."""
        # Recalcula o estado "não salvas" a partir da baseline em vez de marcar
        # como sujo cegamente — carregar/undo/redo não deveriam sujar a aba.
        self.ctx.edit_history.sync_dirty()
        if self.ctx.status_bar:
            line, col = self.cursor_location
            self.ctx.status_bar.update_status(line + 1, col, self.ctx.current_file or "Novo Arquivo")

    # ── Ciclo de vida do buffer ──────────────────────────────────────────

    def set_text(self, text: str) -> None:
        self.load_text(text)
        self.ctx.events.emit(FILE_CHANGED, self.ctx.current_file)

    def load_text(self, text: str):
        super().load_text(text)
        self._after_content_load(text)

    def _after_content_load(self, text: str) -> None:
        """Reseta undo/dirty e registra a baseline do buffer recém-carregado."""
        self.ctx.edit_history.on_content_loaded(text)
        self.ctx.is_dirty = False

    # ── Conversão de índices ─────────────────────────────────────────────

    @property
    def _lines(self):
        return self.document.lines or [""]

    def _to_location(self, index) -> Tuple[int, int]:
        """Converte um índice Tk (``"3.14"``, ``"insert"``, ``"end"``) em ``(linha, coluna)``."""
        if not isinstance(index, str):
            return tuple(index)

        spec = index.strip()
        if spec in ("", "insert"):
            return tuple(self.cursor_location)
        if spec == "end":
            lines = self._lines
            return (len(lines) - 1, len(lines[-1]))
        if spec in ("sel.first", "sel.last"):
            sel = sorted((tuple(self.selection.start), tuple(self.selection.end)))
            return sel[0] if spec == "sel.first" else sel[1]

        offset_match = _OFFSET_SUFFIX.match(spec)
        if offset_match:
            base = self._to_location(offset_match.group("base") or "insert")
            delta = int(offset_match.group("n"))
            if offset_match.group("sign") == "-":
                delta = -delta
            return self._offset_to_location(self._location_to_offset(base) + delta)

        line_str, _, col_str = spec.partition(".")
        line = max(1, int(line_str or 1))
        col = int(col_str or 0)
        lines = self._lines
        row = min(line - 1, len(lines) - 1)
        return (row, min(col, len(lines[row])))

    def _location_to_offset(self, location) -> int:
        """Offset absoluto (em caracteres) de uma posição do documento."""
        text = self.text
        row, col = location
        offset = 0
        for _ in range(row):
            nxt = text.find("\n", offset)
            if nxt == -1:
                return len(text)
            offset = nxt + 1
        return min(len(text), offset + max(0, col))

    def _offset_to_location(self, offset: int) -> Tuple[int, int]:
        text = self.text
        offset = max(0, min(len(text), offset))
        line_start = text.rfind("\n", 0, offset) + 1
        return (text.count("\n", 0, offset), offset - line_start)

    # ── Protocolo TextEditor ─────────────────────────────────────────────

    def insert(self, text: str, index: str = "insert", **kwargs) -> None:
        super().insert(text, self._to_location(index), **kwargs)

    def delete(self, start: str, end: Optional[str] = None) -> None:
        start_off = self._location_to_offset(self._to_location(start))
        end_off = start_off + 1 if end is None else self._location_to_offset(self._to_location(end))
        if end_off > start_off:
            super().delete(self._offset_to_location(start_off), self._offset_to_location(end_off))

    def get_text(self, start: str = "1.0", end: str = "end") -> str:
        if start == "1.0" and end == "end":
            return self.text
        return self.get_text_range(self._to_location(start), self._to_location(end))

    def get_cursor_index(self) -> str:
        row, col = self.cursor_location
        return f"{row + 1}.{col}"

    def set_cursor(self, index: str) -> None:
        self.move_cursor(self._to_location(index))

    def get_selection_range(self) -> Optional[Tuple[str, str]]:
        selection = self.selection
        if selection.is_empty:
            return None
        (start_row, start_col), (end_row, end_col) = sorted(
            (tuple(selection.start), tuple(selection.end))
        )
        return (f"{start_row + 1}.{start_col}", f"{end_row + 1}.{end_col}")

    def set_selection_range(self, start: str, end: str) -> None:
        selection_type = type(self.selection)
        self.selection = selection_type(self._to_location(start), self._to_location(end))

    def index_offset(self, index: str, chars: int) -> str:
        offset = self._location_to_offset(self._to_location(index)) + chars
        row, col = self._offset_to_location(offset)
        return f"{row + 1}.{col}"

    def get_char_at(self, index: str) -> str:
        text = self.text
        offset = self._location_to_offset(self._to_location(index))
        return text[offset] if offset < len(text) else ""

    def get_line_count(self) -> int:
        return len(self.document.lines)

    def bind_key(self, key: str, callback: Callable[[EditorEvent], Any]) -> None:
        """Registra um callback para uma tecla na sintaxe Tk.

        O Textual não tem binding por-widget (`Widget.bind` não existe), então as
        teclas são normalizadas e despachadas em `handle_key`.
        """
        self._key_callbacks[self._tk_key_to_textual(key)] = callback

    @staticmethod
    def _tk_key_to_textual(key: str) -> str:
        spec = key.strip()
        if spec.startswith("<") and spec.endswith(">"):
            spec = spec[1:-1]
        if spec.split("-", 1)[0] in _GENERIC_TK_EVENTS:
            return "*"
        parts = spec.split("-")
        modifiers = []
        for raw in parts[:-1]:
            mapped = _TK_MODIFIERS.get(raw, raw.lower())
            if mapped not in modifiers:
                modifiers.append(mapped)
        modifiers.append(parts[-1].lower())
        return "+".join(modifiers)

    async def _on_key(self, event: events.Key) -> None:
        """Despacha a tecla para os callbacks de `bind_key` antes do Textual.

        O `TextArea` implementa `_on_key` próprio e não chama `handle_key`,
        então é aqui que as teclas registradas em `bind_key` entram.
        """
        if self.handle_key(event):
            event.stop()
            event.prevent_default()
            return
        await super()._on_key(event)

    def handle_key(self, event: events.Key) -> bool:
        """Executa o callback da tecla; `True` quando a tecla foi consumida.

        Um retorno ``"break"`` (semântica do Tk) cancela a inserção padrão do
        `TextArea`; qualquer outro valor deixa o comportamento padrão seguir.
        """
        callback = self._key_callbacks.get(event.key)
        if callback is None and event.is_printable:
            callback = self._key_callbacks.get("*")
        if callback is None:
            return False
        result = callback(EditorEvent(char=event.character or "", keysym=event.key))
        return result == "break"

    # ── Undo / Redo ──────────────────────────────────────────────────────

    def edit_separator(self) -> None:
        """Força o próximo edit a abrir um novo lote de undo."""
        self.history.checkpoint()

    def reset_undo_stack(self) -> None:
        self.history.clear()

    def begin_undo_group(self) -> None:
        # O Textual agrupa os edits automaticamente; não há análogo ao
        # `autoseparators=False` do Tk.
        return None

    def end_undo_group(self) -> None:
        self.history.checkpoint()

    def is_in_transaction(self) -> bool:
        return self.ctx.edit_history.is_in_transaction

    # ── Tags do Tk (sem equivalente no Textual) ──────────────────────────

    def apply_tag(self, tag_name: str, start: str, end: str) -> None:
        """No-op: o Textual usa highlighters, não tags do Tk."""
        return None

    def configure_tag(self, tag_name: str, **kwargs) -> None:
        """No-op: o Textual usa highlighters, não tags do Tk."""
        return None

    def get_tags(self) -> Tuple[str, ...]:
        return tuple()

    def delete_tag(self, tag_name: str) -> None:
        """No-op: o Textual usa highlighters, não tags do Tk."""
        return None

    def remove_tag(self, tag_name: str, start: str, end: str) -> None:
        """No-op: o Textual usa highlighters, não tags do Tk."""
        return None

    # ── Navegação rápida (Alt + Setas + Número) ──────────────────────────

    def move_cursor_by_lines(self, lines: int, direction: str) -> None:
        """
        Move o cursor N linhas para cima ou para baixo.

        Args:
            lines: Quantidade de linhas para mover (1-9)
            direction: "up" ou "down"
        """
        try:
            current_line, current_col = self.cursor_location
            total_lines = len(self.text.splitlines())

            if direction == "up":
                new_line = max(0, current_line - lines)
            else:  # down
                new_line = min(total_lines - 1, current_line + lines)

            self.cursor_location = (new_line, 0)
        except (ValueError, AttributeError):
            pass


def missing_protocol_methods() -> list:
    """Métodos do protocolo `TextEditor` que esta classe ainda não implementa.

    `EditorArea` não pode herdar de `TextEditor` (metaclass do `Protocol` é
    incompatível com a do `TextArea`), então a conformidade é verificada aqui —
    uma lista vazia significa que o protocolo está completo.
    """
    return sorted(
        name for name in dir(TextEditor)
        if not name.startswith("_") and not hasattr(EditorArea, name)
    )
