#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import json
import os
from typing import List, Optional

class ThemeManager:
    """Gerencia temas JSON para a UI e fornece uma lista de temas disponíveis."""

    @staticmethod
    def get_theme_dir() -> str:
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "ui", "estilo"))

    @staticmethod
    def list_themes() -> List[str]:
        theme_dir = ThemeManager.get_theme_dir()
        if not os.path.isdir(theme_dir):
            return []
        return sorted([name for name in os.listdir(theme_dir) if name.lower().endswith(".json")])

    @staticmethod
    def resolve_theme_path(theme_name: Optional[str]) -> str:
        theme_dir = ThemeManager.get_theme_dir()
        if not theme_name:
            return os.path.join(theme_dir, "editor.json")
        theme_file = theme_name if theme_name.lower().endswith(".json") else f"{theme_name}.json"
        return os.path.join(theme_dir, theme_file)

    @staticmethod
    def load_theme(theme_name: Optional[str] = None) -> dict:
        theme_path = ThemeManager.resolve_theme_path(theme_name)
        if not os.path.exists(theme_path):
            themes = ThemeManager.list_themes()
            if themes:
                theme_path = os.path.join(ThemeManager.get_theme_dir(), themes[0])
            else:
                return {}

        try:
            with open(theme_path, "r", encoding="utf-8") as theme_file:
                theme = json.load(theme_file)
                if isinstance(theme, dict):
                    return theme
        except Exception:
            pass
        return {}

    @staticmethod
    def get_theme_name(theme_name: Optional[str]) -> str:
        if not theme_name:
            return "editor"
        return os.path.splitext(os.path.basename(theme_name))[0]

    @staticmethod
    def get_theme_display_list() -> List[str]:
        return [os.path.splitext(name)[0] for name in ThemeManager.list_themes()]
