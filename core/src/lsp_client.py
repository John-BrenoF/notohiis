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
        self.responses = {}
        self.callbacks = {}

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            # Inicia thread de leitura para capturar respostas do servidor
            threading.Thread(target=self._read_loop, daemon=True).start()
            print(f"[LSP] Servidor iniciado: {' '.join(self.server_command)}")
        except FileNotFoundError:
            print(f"[LSP] Servidor '{self.server_command[0]}' não encontrado. Autocompletar inteligente desativado.")
        except Exception as e:
            print(f"[LSP] Erro ao iniciar servidor: {e}")

    def _read_loop(self):
        """Lê continuamente as mensagens do servidor seguindo a especificação LSP."""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline().decode('utf-8')
                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())
                    self.process.stdout.readline() # Pula \r\n
                    content = self.process.stdout.read(length).decode('utf-8')
                    data = json.loads(content)
                    if "id" in data:
                        req_id = data["id"]
                        if req_id in self.callbacks:
                            callback = self.callbacks.pop(req_id)
                            callback(data)
                        else:
                            self.responses[req_id] = data
            except Exception:
                break

    def send_notification(self, method: str, params: Dict[str, Any]):
        """Envia notificações (mensagens sem ID, como didOpen)."""
        if not self.process or not self.process.stdin:
            return

        content = {"jsonrpc": "2.0", "method": method, "params": params}
        body = json.dumps(content)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        try:
            self.process.stdin.write(header.encode("ascii") + body.encode("utf-8"))
            self.process.stdin.flush()
        except (BrokenPipeError, AttributeError):
            print(f"[LSP] Falha ao enviar notificação {method}: Processo não disponível.")

    def send_request(self, method: str, params: Dict[str, Any], callback=None):
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
        if callback:
            self.callbacks[self.request_id] = callback
            
        body = json.dumps(content)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        
        try:
            self.process.stdin.write(header.encode("ascii"))
            self.process.stdin.write(body.encode("utf-8"))
            self.process.stdin.flush()
        except Exception as e:
            print(f"[LSP] Erro de escrita no servidor: {e}")
        return self.request_id

    def stop(self):
        if self.process:
            self.process.terminate()