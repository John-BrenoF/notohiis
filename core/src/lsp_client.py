import subprocess
import json
import threading
from typing import Optional, Dict, Any

class LSPClient:
    """
    Implementação simplificada de um cliente LSP (Language Server Protocol).
    Gerencia a comunicação JSON-RPC com servidores como pyright ou jedi-language-server.
    """
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            print(f"[LSP] Servidor iniciado: {' '.join(self.server_command)}")
        except Exception as e:
            print(f"[LSP] Erro ao iniciar servidor: {e}")

    def send_request(self, method: str, params: Dict[str, Any]):
        """Envia uma requisição formatada em JSON-RPC (especificação LSP)."""
        if not self.process or not self.process.stdin:
            return

        self.request_id += 1
        content = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        body = json.dumps(content)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        
        try:
            self.process.stdin.write(header.encode("ascii"))
            self.process.stdin.write(body.encode("utf-8"))
            self.process.stdin.flush()
        except Exception as e:
            print(f"[LSP] Erro de escrita no servidor: {e}")

    def stop(self):
        if self.process:
            self.process.terminate()