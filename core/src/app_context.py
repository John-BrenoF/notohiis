import os
from typing import Optional, Any
from core.interfaces import TextEditor, StatusBar, Sidebar, AppWindow
from core.events import EventBus

class AppContext:
    """
    Singleton para gerenciar o estado global da aplicação e 
    permitir a comunicação entre componentes sem acoplamento direto.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppContext, cls).__new__(cls)
            cls._instance.window: Optional[AppWindow] = None
            cls._instance.editor: Optional[TextEditor] = None
            cls._instance.sidebar: Optional[Sidebar] = None
            cls._instance.status_bar: Optional[StatusBar] = None
            cls._instance.current_file: Optional[str] = None
            cls._instance.project_root: Optional[str] = None
            cls._instance.is_dirty: bool = False
            cls._instance._undo_stack_at_save: Optional[int] = 0
            cls._instance._current_undo_index: int = 0
            cls._instance._transaction_level: int = 0
            cls._instance.is_processing_history: bool = False
            cls._instance._chars_since_sep: int = 0
            cls._instance.events = EventBus()
            # Registrador de Plugins
            cls._instance.git_plugin = None
            cls._instance.md_plugin = None
            cls._instance.py_plugin = None
            cls._instance.theme = {}
            cls._instance.selected_theme = None
            cls._instance.external_plugins = []
            cls._instance.autocomplete_engine = None
            cls._instance.smart_tab_hiding = True
            cls._instance.tab_manager = None
            cls._instance.tab_bridge = None
        return cls._instance

    def set_window(self, window: AppWindow):
        self.window = window

    def set_editor(self, editor: TextEditor):
        self.editor = editor

    def set_sidebar(self, sidebar: Sidebar):
        self.sidebar = sidebar

    def set_status_bar(self, status_bar: StatusBar):
        self.status_bar = status_bar

    def set_theme(self, theme: dict, theme_name: Optional[str] = None):
        """Atualiza o tema global e notifica listeners de mudança de tema."""
        self.theme = theme or {}
        self.selected_theme = os.path.splitext(os.path.basename(theme_name))[0] if theme_name else None
        self.events.emit("theme_changed", self.theme)

    def notify_save(self):
        """
        Marca o ponto atual na pilha de desfazer como o estado 'salvo'.
        Chamado pelo BufferManager ou ShortcutManager após gravação em disco.
        """
        self._undo_stack_at_save = self._current_undo_index
        self.is_dirty = False

    def handle_typing(self, char: Optional[str]):
        """
        Gerencia a entrada de texto para criar pontos de Undo granulares.
        Chamado pela UI a cada tecla pressionada.
        """
        self.is_dirty = True
        
        if not self.editor or self.is_processing_history:
            return

        # Caracteres de controle não incrementam a granularidade
        if char is None or len(char) == 0:
            return

        # Definimos separadores lógicos: espaços, pontuação, símbolos e quebras de linha
        logical_separators = (" ", "\n", "\t", ".", ",", "!", "?", ";", ":", "(", "[", "{", "=", "+", "-", "*", "/", "\\")
        
        self._chars_since_sep += 1
        
        # Se for um separador ou o usuário digitou muito (15 chars), criamos um ponto de restauração
        if char in logical_separators or self._chars_since_sep >= 15:
            self.editor.edit_separator()
            self._chars_since_sep = 0
            self.update_undo_index(1, is_new_action=True)

    def update_undo_index(self, change: int, is_new_action: bool = False):
        """
        Atualiza o índice atual da pilha de undo e recalcula is_dirty.
        is_new_action: True se for uma nova digitação (que invalida o Redo).
        """
        if self.is_processing_history:
            return

        # Se o usuário digitar algo novo após um Undo, o "Futuro" (Redo) é descartado.
        # Se o ponto de salvamento estava naquele futuro, ele nunca mais será alcançado.
        if is_new_action and self._undo_stack_at_save is not None:
            if self._current_undo_index < self._undo_stack_at_save:
                self._undo_stack_at_save = None # Invalida o save point original

        self._current_undo_index += change
        
        # Se o índice atual voltou para onde estava no último save, não está mais dirty
        new_dirty_state = self._current_undo_index != self._undo_stack_at_save
        
        if new_dirty_state != self.is_dirty:
            self.is_dirty = new_dirty_state
            self._refresh_ui_status()

    def begin_transaction(self):
        """Inicia um grupo de operações que devem ser desfeitas juntas."""
        if self._transaction_level == 0 and self.editor:
            self.editor.begin_undo_group()
            self._chars_since_sep = 0
        self._transaction_level += 1

    def end_transaction(self):
        """Finaliza o grupo de operações atômicas."""
        self._transaction_level = max(0, self._transaction_level - 1)
        if self._transaction_level == 0 and self.editor:
            self.editor.end_undo_group()
            self.update_undo_index(1, is_new_action=True)

    def perform_undo(self):
        if self.editor and not self.is_processing_history:
            # Garante que o que está sendo digitado seja "fechado" antes de desfazer
            if self._chars_since_sep > 0:
                self.editor.edit_separator()
                self._chars_since_sep = 0
            
            self.is_processing_history = True
            self.editor.undo()
            self.update_undo_index(-1)
            self.is_processing_history = False

    def perform_redo(self):
        if self.editor and not self.is_processing_history:
            self.is_processing_history = True
            self.editor.redo()
            self.update_undo_index(1)
            self.is_processing_history = False

    def _refresh_ui_status(self):
        """Atualiza a StatusBar para refletir mudanças no estado Dirty."""
        if self.status_bar and self.editor:
            idx = self.editor.get_cursor_index()
            line, col = idx.split(".")
            self.status_bar.update_status(int(line), int(col), self.current_file)