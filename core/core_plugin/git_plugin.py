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

    def get_git_info(self) -> Tuple[str, bool]:
        """Retorna (branch_name, is_dirty) de forma síncrona."""
        root = self.ctx.project_root
        if not root:
            return "", False
        
        try:
            # Obter Branch
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
            
            # Verificar se está Dirty
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
            
            return branch, len(status) > 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "", False

    def async_update_status(self):
        """Atualiza a StatusBar sem travar a UI principal."""
        def task():
            branch, dirty = self.get_git_info()
            if self.ctx.status_bar and branch:
                status_str = f" {branch}" + ("*" if dirty else "")
                # CustomTkinter/Tkinter exige atualização na thread principal
                self.ctx.window.after(0, lambda: self.ctx.status_bar.git_label.configure(text=status_str))
        
        threading.Thread(target=task, daemon=True).start()

    def quick_commit_ui(self):
        """Abre uma janela flutuante para commit rápido."""
        if not self.ctx.project_root:
            return

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.title("Git Quick Commit")
        dialog.geometry("400x200")
        dialog.attributes("-topmost", True)

        label = ctk.CTkLabel(dialog, text="Mensagem de Commit:")
        label.pack(pady=10)

        entry = ctk.CTkEntry(dialog, width=300)
        entry.pack(pady=5)
        entry.focus_set()

        def execute_commit():
            msg = entry.get()
            if msg:
                try:
                    subprocess.run(["git", "add", "."], cwd=self.ctx.project_root, check=True)
                    subprocess.run(["git", "commit", "-m", msg], cwd=self.ctx.project_root, check=True)
                    self.async_update_status()
                    dialog.destroy()
                except subprocess.CalledProcessError as e:
                    print(f"Erro no commit: {e}")

        btn = ctk.CTkButton(dialog, text="Commit", command=execute_commit)
        btn.pack(pady=20)
        
        dialog.bind("<Return>", lambda e: execute_commit())