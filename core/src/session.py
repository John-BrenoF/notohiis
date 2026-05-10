import json
import os
from typing import Optional

class SessionManager:
    """Gerencia a persistência de estado do editor (último diretório)."""
    SESSION_FILE = ".session_config"
    MAX_RECENT = 10

    @staticmethod
    def save_session(project_root: Optional[str]):
        if not project_root: return
        
        data = {}
        if os.path.exists(SessionManager.SESSION_FILE):
            try:
                with open(SessionManager.SESSION_FILE, 'r') as f:
                    data = json.load(f)
            except Exception: pass
            
        recent = data.get("recent_projects", [])
        if project_root in recent: recent.remove(project_root)
        recent.insert(0, project_root)
        
        data["last_project_root"] = project_root
        data["recent_projects"] = recent[:SessionManager.MAX_RECENT]
        
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

    @staticmethod
    def get_recent_projects() -> list:
        if not os.path.exists(SessionManager.SESSION_FILE): return []
        try:
            with open(SessionManager.SESSION_FILE, 'r') as f:
                return json.load(f).get("recent_projects", [])
        except Exception: return []