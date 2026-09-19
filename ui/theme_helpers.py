#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

"""
Helpers para acesso consistente a cores do tema.
Elimina a repetição de `theme.get("editor", {}).get("bg", "#...")` espalhada pela UI.
"""

from typing import Any
from core.src.app_context import AppContext


def get_theme(section: str, key: str, default: Any = None) -> Any:
    """Obtém um valor do tema de forma segura.
    
    Uso:
        bg = get_theme("editor", "bg", "#1e1e1e")
    """
    return AppContext().theme.get(section, {}).get(key, default)


def editor_color(key: str, default: str = "") -> str:
    """Atalho para cores da seção 'editor' do tema."""
    return get_theme("editor", key, default)


def sidebar_color(key: str, default: str = "") -> str:
    """Atalho para cores da seção 'sidebar' do tema."""
    return get_theme("sidebar", key, default)


def status_bar_color(key: str, default: str = "") -> str:
    """Atalho para cores da seção 'status_bar' do tema."""
    return get_theme("status_bar", key, default)


def syntax_color(key: str, default: str = "") -> str:
    """Atalho para cores da seção 'syntax' do tema."""
    return get_theme("syntax", key, default)


# Cores padrão (fallback quando nenhum tema está carregado)
DEFAULT_COLORS = {
    "editor_bg": "#1e1e1e",
    "editor_fg": "#d4d4d4",
    "editor_cursor": "white",
    "editor_selection_bg": "#264f78",
    "editor_gutter_bg": "#1e1e1e",
    "editor_gutter_fg": "#858585",
    "sidebar_bg": "#1a1a1c",
    "sidebar_fg": "#cccccc",
    "sidebar_hover": "#2d2d2d",
    "sidebar_label": "gray",
    "sidebar_selected": "#3a3f4b",
    "status_bg": "#21252b",
    "status_fg": "#9da5b4",
    "status_hover": "#2c313a",
    "menu_bg": "#282c34",
    "menu_fg": "#dcdfe4",
    "menu_hover": "#3f4b61",
    "menu_border": "#3e4451",
    "menu_separator": "#3e4451",
    "menu_heading": "#7b828e",
}
