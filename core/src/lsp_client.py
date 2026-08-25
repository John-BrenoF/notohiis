import subprocess
import json
import threading
import shutil
from typing import Optional, Dict, Any, Callable


class LSPClient:
    """
    Implementação simplificada de um cliente LSP (Language Server Protocol).
    Gerencia a comunicação JSON-RPC com servidores como pyright ou jedi-language-server.
    """
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._callbacks: Dict[int, Callable] = {}
        self._responses: Dict[int, dict] = {}
        self._read_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
            self._stderr_thread.start()
            print(f"[LSP] Servidor iniciado: {' '.join(self.server_command)}")
        except FileNotFoundError:
            print(f"[LSP] Servidor '{self.server_command[0]}' não encontrado.")
        except Exception as e:
            print(f"[LSP] Erro ao iniciar servidor: {e}")

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _read_exact(self, stream, length: int) -> bytes:
        buffer = bytearray()
        while len(buffer) < length:
            chunk = stream.read(length - len(buffer))
            if not chunk:
                break
            buffer.extend(chunk)
        return bytes(buffer)

    def _read_line(self, stream) -> bytes:
        buffer = bytearray()
        while True:
            byte = stream.read(1)
            if not byte:
                break
            buffer.extend(byte)
            if byte == b'\n':
                break
        return bytes(buffer)

    def _read_loop(self):
        while self.is_alive():
            try:
                header_line = self._read_line(self.process.stdout)
                if not header_line:
                    break
                header_str = header_line.decode('utf-8')
                if not header_str.startswith("Content-Length:"):
                    continue
                length = int(header_str.split(":")[1].strip())
                while True:
                    sep = self._read_line(self.process.stdout)
                    if not sep or sep == b'\r\n':
                        break
                raw = self._read_exact(self.process.stdout, length)
                if len(raw) < length:
                    break
                data = json.loads(raw.decode('utf-8'))
                self._dispatch_response(data)
            except Exception as e:
                print(f"[LSP] Erro na leitura: {e}")
                break

    def _dispatch_response(self, data: dict):
        if "id" not in data:
            return
        req_id = data["id"]
        with self._lock:
            if req_id in self._callbacks:
                callback = self._callbacks.pop(req_id)
                callback(data)
            else:
                self._responses[req_id] = data

    def _drain_stderr(self):
        while self.is_alive():
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='replace').strip()
                if text:
                    print(f"[LSP stderr] {text}")
            except Exception:
                break

    def _send_raw(self, data: bytes):
        with self._write_lock:
            self.process.stdin.write(data)
            self.process.stdin.flush()

    def send_notification(self, method: str, params: Dict[str, Any]):
        if not self.is_alive() or not self.process.stdin:
            return
        content = {"jsonrpc": "2.0", "method": method, "params": params}
        body = json.dumps(content)
        encoded = body.encode("utf-8")
        header = f"Content-Length: {len(encoded)}\r\n\r\n"
        try:
            self._send_raw(header.encode("ascii") + encoded)
        except (BrokenPipeError, OSError):
            print(f"[LSP] Falha ao enviar notificação {method}.")

    def send_request(self, method: str, params: Dict[str, Any], callback: Optional[Callable] = None) -> Optional[int]:
        if not self.is_alive() or not self.process.stdin:
            return None
        with self._lock:
            self.request_id += 1
            req_id = self.request_id
            if callback:
                self._callbacks[req_id] = callback
        content = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        body = json.dumps(content)
        encoded = body.encode("utf-8")
        header = f"Content-Length: {len(encoded)}\r\n\r\n"
        try:
            self._send_raw(header.encode("ascii") + encoded)
        except (BrokenPipeError, OSError) as e:
            print(f"[LSP] Erro ao enviar requisição {method}: {e}")
            return None
        return req_id

    def stop(self):
        if not self.process:
            return
        try:
            self.send_request("shutdown", {})
            self.send_notification("exit", {})
        except Exception:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()


def detect_lsp_server() -> Optional[list]:
    candidates = [
        ["jedi-language-server"],
        ["pyright-langserver", "--stdio"],
        ["pylsp"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            return cmd
    return None