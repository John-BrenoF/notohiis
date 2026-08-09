import json
import os

def get_infor(key: str, default: str = "Desconhecida") -> str:
    path = os.path.join(os.getcwd(), "infor_app", "infor.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return str(json.load(f).get(key, default))
    except Exception:
        return str(default)