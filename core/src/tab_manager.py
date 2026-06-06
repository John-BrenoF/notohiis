import os
from dataclasses import dataclass
from typing import List, Optional
from core.src.buffer import BufferManager

@dataclass
class Tab:
    id: int
    path: Optional[str] = None
    content: str = ""
    title: str = "Novo Arquivo"
    is_dirty: bool = False

    @property
    def display_name(self) -> str:
        if self.path:
            return os.path.basename(self.path) or self.title
        return self.title

class TabManager:
    """Gerencia uma coleção simples de abas de edição de texto."""

    def __init__(self):
        self.tabs: List[Tab] = []
        self._next_id = 1
        self.active_tab_id: Optional[int] = None

    def create_tab(self, path: Optional[str] = None, content: Optional[str] = None, set_active: bool = True) -> Tab:
        if path and content is None:
            content = BufferManager.read_file(path)
        if content is None:
            content = ""

        title = os.path.basename(path) if path else "Novo Arquivo"
        tab = Tab(
            id=self._next_id,
            path=path,
            content=content,
            title=title or "Novo Arquivo",
            is_dirty=False
        )
        self._next_id += 1
        self.tabs.append(tab)
        if set_active:
            self.select_tab(tab.id)
        return tab

    def open_file(self, path: str) -> Tab:
        existing = self.find_tab_by_path(path)
        if existing:
            self.select_tab(existing.id)
            return existing
        return self.create_tab(path=path)

    def find_tab_by_path(self, path: str) -> Optional[Tab]:
        for tab in self.tabs:
            if tab.path == path:
                return tab
        return None

    def get_active_tab(self) -> Optional[Tab]:
        return next((tab for tab in self.tabs if tab.id == self.active_tab_id), None)

    def select_tab(self, tab_id: int) -> Optional[Tab]:
        if self.active_tab_id == tab_id:
            return self.get_active_tab()
        if any(tab.id == tab_id for tab in self.tabs):
            self.active_tab_id = tab_id
            return self.get_active_tab()
        return None

    def update_active_content(self, content: str):
        tab = self.get_active_tab()
        if not tab:
            return
        if tab.content != content:
            tab.content = content
            tab.is_dirty = True

    def mark_active_saved(self):
        tab = self.get_active_tab()
        if not tab:
            return
        tab.is_dirty = False

    def save_active_tab(self) -> bool:
        tab = self.get_active_tab()
        if not tab or not tab.path:
            return False
        if BufferManager.save_file(tab.path, tab.content):
            tab.is_dirty = False
            return True
        return False

    def update_tab_path(self, tab_id: int, new_path: str):
        tab = next((t for t in self.tabs if t.id == tab_id), None)
        if not tab:
            return
        tab.path = new_path
        tab.title = os.path.basename(new_path) or tab.title

    def close_tab(self, tab_id: int, force: bool = False) -> bool:
        tab = next((t for t in self.tabs if t.id == tab_id), None)
        if not tab:
            return True
        if tab.is_dirty and not force:
            return False
        self.tabs = [t for t in self.tabs if t.id != tab_id]
        if self.active_tab_id == tab_id:
            self.active_tab_id = self.tabs[-1].id if self.tabs else None
        return True

    def get_tabs(self) -> List[Tab]:
        return self.tabs[:] 
