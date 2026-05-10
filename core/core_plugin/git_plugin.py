import subprocess
import threading
from typing import Optional, Tuple
import customtkinter as ctk
from core.src.app_context import AppContext

class GitPlugin:
    """
    Plugin para integração com Git.
    Responsável por monitorar o estado do repositório e realizar commits rápidos.
    """
    def __init__(self):
        self.ctx = AppContext()

    def is_git_repo(self, path: str) -> bool:
        """Verifica se o caminho é um repositório git válido."""
        try:
            subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], 
                                    cwd=path, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def get_git_info(self) -> Tuple[str, int]:
        """Retorna (branch_name, num_changes) de forma síncrona."""
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return "", 0
        
        try:
            # Obter Branch
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
            
            # Verificar se está Dirty e contar arquivos
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
            
            num_changes = len(status.splitlines()) if status else 0
            return branch, num_changes
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "", 0

    def get_changed_files(self) -> str:
        """Retorna a lista de arquivos modificados (status --short)."""
        root = self.ctx.project_root
        if not root: return ""
        try:
            return subprocess.check_output(
                ["git", "status", "--short"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return ""

    def async_update_status(self):
        """Atualiza a StatusBar sem travar a UI principal."""
        def task():
            branch, changes = self.get_git_info()
            if self.ctx.status_bar and branch:
                status_str = f"󰊢 {branch}" + (f" ({changes})" if changes > 0 else "")
                self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui(status_str, changes > 0))
            elif self.ctx.status_bar and self.ctx.status_bar.git_button: # Se não há branch, limpa o texto do botão
                self.ctx.window.after(0, lambda: self.ctx.status_bar.git_button.configure(text=""))
        
        threading.Thread(target=task, daemon=True).start()

    def quick_commit_ui(self):
        """Abre uma janela flutuante para commit rápido."""
        if not self.ctx.project_root or not self.is_git_repo(self.ctx.project_root):
            return

        changed_files = self.get_changed_files()
        if not changed_files:
            return # Nada para commitar

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.title("󰊢 Git Quick Commit")
        dialog.geometry("450x400")
        dialog.attributes("-topmost", True)
        
        # Centralização básica (pode usar o helper do ShortcutManager se preferir)
        dialog.focus_set()

        ctk.CTkLabel(dialog, text="Arquivos Alterados:", font=("Segoe UI", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        
        # Lista de arquivos (Visualização apenas)
        text_area = ctk.CTkTextbox(dialog, height=150, font=("Consolas", 11))
        text_area.pack(fill="x", padx=20, pady=5)
        text_area.insert("1.0", changed_files)
        text_area.configure(state="disabled")

        ctk.CTkLabel(dialog, text="Mensagem de Commit:").pack(pady=(10, 0), padx=20, anchor="w")
        entry = ctk.CTkEntry(dialog, width=410, placeholder_text="O que você mudou?")
        entry.pack(pady=5, padx=20)
        entry.focus_set()

        def execute_commit():
            msg = entry.get()
            if msg:
                btn.configure(state="disabled", text="󰊢 Commitando...")
                def task():
                    try:
                        subprocess.run(["git", "add", "."], cwd=self.ctx.project_root, check=True)
                        subprocess.run(["git", "commit", "-m", msg], cwd=self.ctx.project_root, check=True)
                        self.ctx.window.after(0, lambda: [
                            self.async_update_status(),
                            dialog.destroy()
                        ])
                    except subprocess.CalledProcessError as e:
                        print(f"Erro no commit: {e}")
                        self.ctx.window.after(0, lambda: btn.configure(state="normal", text="󰊢 Commit"))
                threading.Thread(target=task, daemon=True).start()

        btn = ctk.CTkButton(dialog, text="󰊢 Commit", command=execute_commit)
        btn.pack(pady=20)
        
        ctk.CTkLabel(dialog, text="Dica: [ENTER] confirma | [ESC] cancela", 
                     font=("Segoe UI", 10), text_color="gray").pack(pady=(0, 10))
        
        dialog.bind("<Return>", lambda e: execute_commit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())