import json
import os
from typing import Optional

class SessionManager:
    """Gerencia a persistência de estado do editor (último diretório)."""
    SESSION_FILE = ".session_config"

    @staticmethod
    def save_session(project_root: Optional[str]):
        data = {"last_project_root": project_root}
        try:
            with open(SessionManager.SESSION_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    @staticmethod
    def load_session() -> Optional[str]:
        if not os.path.exists(SessionManager.SESSION_FILE):
            return None
        try:
            with open(SessionManager.SESSION_FILE, 'r') as f:
                data = json.load(f)
                path = data.get("last_project_root")
                return path if path and os.path.exists(path) else None
        except Exception:
            return None