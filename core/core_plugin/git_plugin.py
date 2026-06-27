import subprocess
import threading
import os
from typing import Optional, Tuple, List
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

    def get_status_data(self) -> List[Tuple[str, str]]:
        """Retorna lista de (status_code, path) relativos do repositório."""
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            output = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=root, stderr=subprocess.DEVNULL, text=True
            ).strip()
            if not output: return []
            
            items = []
            for line in output.splitlines():
                if len(line) >= 4:
                    code = line[:2] # Ex: 'M ', 'A ', '??'
                    path = line[3:].strip().strip('"')
                    items.append((code, path))
            return items
        except Exception:
            return []

    def decorate_sidebar(self):
        """Aplica cores aos itens da sidebar com base no status do Git sem acoplar a Sidebar."""
        if not self.ctx.sidebar or not hasattr(self.ctx.sidebar, "item_widgets"):
            return

        root = self.ctx.project_root
        status_data = self.get_status_data()
        
        # Cores padrão do tema Atom/OneDark
        colors = {"mod": "#e5c07b", "add": "#98c379", "del": "#e06c75"}
        theme_fg = self.ctx.theme.get("sidebar", {}).get("fg", "#cccccc")

        # Mapeia caminho absoluto -> (caractere_status, cor)
        status_map = {}
        for code, rel_path in status_data:
            abs_path = os.path.abspath(os.path.join(root, rel_path))
            char = ""
            color = theme_fg
            if 'M' in code: char = "M"; color = colors["mod"]
            elif 'A' in code or '?' in code: char = "A"; color = colors["add"]
            elif 'D' in code: char = "D"; color = colors["del"]
            elif 'R' in code: char = "R"; color = colors["mod"]
            
            if char:
                status_map[abs_path] = (char, color)

        def update_ui():
            # Tiramos uma cópia dos itens para evitar erros de concorrência com a UI
            items = list(self.ctx.sidebar.item_widgets.items())
            for path, btn in items:
                abs_path = os.path.abspath(path)
                current_text = btn.cget("text")
                
                # Limpa prefixos de status anteriores para evitar acúmulo (ex: "[M] [M] arquivo.py")
                # O padrão esperado é "[X] " onde X é o status
                if current_text.startswith("[") and "] " in current_text:
                    clean_text = current_text.split("] ", 1)[1]
                else:
                    clean_text = current_text

                if abs_path in status_map:
                    char, color = status_map[abs_path]
                    # Adiciona o status como prefixo. O layout do botão cuida do espaçamento.
                    btn.configure(text=f"[{char}] {clean_text}", text_color=color)
                else:
                    # Se não houver status (ou foi resolvido), volta ao texto original e cor do tema
                    btn.configure(text=clean_text, text_color=theme_fg)

                try:
                    pass # A configuração já foi feita acima
                except: pass
        
        self.ctx.window.after(0, update_ui)

    def async_update_status(self):
        """Atualiza a StatusBar sem travar a UI principal."""
        def task():
            branch, changes = self.get_git_info()
            is_repo = self.is_git_repo(self.ctx.project_root) if self.ctx.project_root else False

            if self.ctx.status_bar:
                if branch:
                    status_str = f"󰊢 {branch}" + (f" ({changes})" if changes > 0 else "")
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui(status_str, changes > 0))
                elif is_repo:
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui("󰊢 (git)", False))
                else:
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui("", False))

            if is_repo:
                # Delay de 50ms para garantir que a Sidebar terminou de recriar os widgets no thread principal
                self.ctx.window.after(50, self.decorate_sidebar)
        
        threading.Thread(target=task, daemon=True).start()

    def get_diff(self, path: str = None) -> str:
        """Retorna o diff do arquivo ou de todo o repo."""
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return ""
        try:
            cmd = ["git", "diff"]
            if path:
                cmd.append(path)
            return subprocess.check_output(cmd, cwd=root, stderr=subprocess.STDOUT, text=True)
        except Exception as e:
            return str(e)

    def stage_file(self, path: str):
        root = self.ctx.project_root
        if root:
            subprocess.run(["git", "add", path], cwd=root)
            self.async_update_status()

    def unstage_file(self, path: str):
        root = self.ctx.project_root
        if root:
            subprocess.run(["git", "reset", "HEAD", path], cwd=root)
            self.async_update_status()

    def get_branches(self) -> List[str]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            output = subprocess.check_output(["git", "branch"], cwd=root, text=True)
            return [line.strip().replace("* ", "") for line in output.splitlines()]
        except Exception:
            return []

    def switch_branch(self, branch_name: str):
        root = self.ctx.project_root
        if root:
            subprocess.run(["git", "checkout", branch_name], cwd=root)
            self.async_update_status()

    def git_push(self):
        root = self.ctx.project_root
        if root:
            threading.Thread(target=lambda: subprocess.run(["git", "push"], cwd=root), daemon=True).start()

    def git_pull(self):
        root = self.ctx.project_root
        if root:
            threading.Thread(target=lambda: [subprocess.run(["git", "pull"], cwd=root), self.async_update_status()], daemon=True).start()

    def quick_commit_ui(self):
        """Abre uma janela flutuante para commit rápido."""
        if not self.ctx.project_root or not self.is_git_repo(self.ctx.project_root):
            return

        status_data = self.get_status_data()
        if not status_data:
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

        # Configurar Tags de cores no widget interno (Tkinter Text)
        text_area._textbox.tag_configure("mod", foreground="#e5c07b")
        text_area._textbox.tag_configure("add", foreground="#98c379")
        text_area._textbox.tag_configure("del", foreground="#e06c75")

        for code, path in status_data:
            tag = None
            if 'M' in code or 'R' in code: tag = "mod"
            elif 'A' in code or '?' in code: tag = "add"
            elif 'D' in code: tag = "del"
            
            text_area._textbox.insert("end", f"{code} ", tag)
            text_area._textbox.insert("end", f"{path}\n")

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