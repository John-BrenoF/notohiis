import json
import os

# Relativo a este arquivo, não ao CWD do processo: o leitor funciona mesmo
# quando o editor é iniciado de outro diretório.
_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def get_infor(key: str, default: str = "Desconhecida") -> str:
    path = os.path.join(_APP_ROOT, "infor_app", "infor.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return str(json.load(f).get(key, default))
    except Exception:
        return str(default)
