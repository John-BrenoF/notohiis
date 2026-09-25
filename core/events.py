from typing import Callable, Dict, List, Any

# ── Eventos bem-conhecidos emitidos pelo aplicativo ─────────────────────────
#
# Use as constantes abaixo (em vez de literais) ao chamar `emit`/`on`, para que
# um typo vire um erro de importação e não um listener silenciosamente morto.
#
#   DIRTY_CHANGED         payload: bool             — estado "não salvo" mudou
#   THEME_CHANGED         payload: dict             — tema global recarregado
#   FILE_CHANGED          payload: str | None        — buffer carregado trocou de arquivo
#   CONTENT_CHANGED       payload: str               — texto do editor foi alterado
#   LINE_NUMBERS_REDRAWN  payload: None              — gutter foi redesenhado

DIRTY_CHANGED = "dirty_changed"
THEME_CHANGED = "theme_changed"
FILE_CHANGED = "file_changed"
CONTENT_CHANGED = "content_changed"
LINE_NUMBERS_REDRAWN = "line_numbers_redrawn"


class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def off(self, event_name: str, callback: Callable):
        """Remove um listener. Útil em `teardown`/troca de contexto."""
        listeners = self._listeners.get(event_name)
        if not listeners:
            return
        try:
            listeners.remove(callback)
        except ValueError:
            pass

    def emit(self, event_name: str, data: Any = None):
        for callback in list(self._listeners.get(event_name, [])):
            callback(data)
