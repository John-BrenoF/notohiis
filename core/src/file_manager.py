import os
import shutil
import subprocess
from typing import List, Dict, Optional


class FileManager:
    """Funções para navegação e manipulação no sistema de arquivos."""

    @staticmethod
    def list_directory(path: str) -> List[Dict[str, str]]:
        """Lista arquivos e pastas em um diretório para o Sidebar.
        
        Retorna lista ordenada: pastas primeiro, depois arquivos, ambos em ordem alfabética.
        """
        if not path or not os.path.exists(path):
            return []
        items = []
        try:
            for entry in os.scandir(path):
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir()
                })
        except PermissionError:
            print(f"[FileManager] Sem permissão para listar: {path}")
        except OSError as e:
            print(f"[FileManager] Erro ao listar '{path}': {e}")
        return sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))

    SYSTEM_PYTHON = "/usr/bin/python3"
    SYSTEM_DIALOG_TIMEOUT = 300

    SYSTEM_DIALOG_SCRIPT = """
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import gi
    from gi.repository import Gio, GLib
    from urllib.parse import unquote, urlparse
    import uuid
except Exception:
    sys.stdout.write("NOTOHIS_DIALOG_UNAVAILABLE")
    sys.exit(0)

initial = sys.argv[1] if len(sys.argv) > 1 else ""
wait_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 300
outcome = ["NOTOHIS_DIALOG_TIMEOUT"]
loop = GLib.MainLoop()

def on_response(connection, sender, object_path, interface, signal, params, user_data=None):
    try:
        code, results = params.unpack()
    except Exception:
        code, results = 1, {}
    uri = results.get("current_uri") or ""
    if not uri and results.get("uris"):
        uri = results["uris"][0]
    if code == 0 and uri.startswith("file://"):
        outcome[0] = "NOTOHIS_DIALOG_OK " + unquote(urlparse(uri).path)
    else:
        outcome[0] = "NOTOHIS_DIALOG_CANCELLED"
    loop.quit()

try:
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    proxy = Gio.DBusProxy.new_sync(
        bus, Gio.DBusProxyFlags.NONE, None,
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.FileChooser",
        None,
    )
    token = "notohis_" + uuid.uuid4().hex
    options = {
        "directory": GLib.Variant("b", True),
        "modal": GLib.Variant("b", True),
        "handle_token": GLib.Variant("s", token),
    }
    if initial:
        options["current_folder"] = GLib.Variant("ay", bytearray(initial.encode("utf-8") + b"\\0"))
    try:
        handle = proxy.call_sync(
            "OpenFile", GLib.Variant("(ssa{sv})", ("", "Abrir projeto", options)),
            Gio.DBusCallFlags.NONE, -1, None,
        )
    except GLib.Error:
        legacy = dict(options, title=GLib.Variant("s", "Abrir projeto"))
        handle = proxy.call_sync(
            "OpenFile", GLib.Variant("(sa{sv})", ("", legacy)),
            Gio.DBusCallFlags.NONE, -1, None,
        )
    for response_interface in ("org.freedesktop.portal.Request", "org.freedesktop.portal.FileChooser"):
        bus.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            response_interface,
            "Response", handle.unpack()[0], None,
            Gio.DBusSignalFlags.NONE, on_response, None,
        )
except Exception:
    sys.stdout.write("NOTOHIS_DIALOG_UNAVAILABLE")
    sys.exit(0)

GLib.timeout_add_seconds(wait_seconds, lambda: (loop.quit(), False)[1])
loop.run()
sys.stdout.write(outcome[0])
"""

    @staticmethod
    def ask_system_directory(initialdir: str = "") -> Optional[str]:
        interpreter = FileManager.SYSTEM_PYTHON
        if not os.path.exists(interpreter):
            interpreter = shutil.which("python3") or ""
        if not interpreter:
            return None
        try:
            completed = subprocess.run(
                [interpreter, "-c", FileManager.SYSTEM_DIALOG_SCRIPT,
                 initialdir or "", str(FileManager.SYSTEM_DIALOG_TIMEOUT)],
                capture_output=True, text=True, encoding="utf-8",
                timeout=FileManager.SYSTEM_DIALOG_TIMEOUT + 20,
            )
        except Exception:
            return None
        output = (completed.stdout or "").strip()
        prefix = "NOTOHIS_DIALOG_OK "
        if output.startswith(prefix):
            return output[len(prefix):] or None
        if output in ("NOTOHIS_DIALOG_CANCELLED", "NOTOHIS_DIALOG_TIMEOUT"):
            return ""
        return None

    @staticmethod
    def create_file(path: str) -> bool:
        """Cria um arquivo vazio no caminho especificado."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                pass
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao criar arquivo '{path}': {e}")
            return False

    @staticmethod
    def create_directory(path: str) -> bool:
        """Cria um diretório (e pais intermediários) no caminho especificado."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao criar diretório '{path}': {e}")
            return False

    @staticmethod
    def rename_path(old_path: str, new_name: str) -> bool:
        """Renomeia um arquivo ou diretório."""
        try:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            os.rename(old_path, new_path)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao renomear '{old_path}' para '{new_name}': {e}")
            return False

    @staticmethod
    def delete_path(path: str) -> bool:
        """Exclui um arquivo ou diretório (recursivamente)."""
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        except (PermissionError, OSError) as e:
            print(f"[FileManager] Erro ao excluir '{path}': {e}")
            return False
