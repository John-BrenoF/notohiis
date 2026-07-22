import subprocess
import threading
import os
from typing import Optional, Tuple, List
import customtkinter as ctk
from core.src.app_context import AppContext


COLORS = {
    "bg": "#1e2127",
    "panel": "#282c34",
    "panel_alt": "#21252b",
    "border": "#3a3f4b",
    "text": "#cccccc",
    "text_dim": "#7f848e",
    "accent": "#61afef",
    "accent_hover": "#4d94d6",
    "mod": "#e5c07b",
    "add": "#98c379",
    "del": "#e06c75",
    "danger": "#e06c75",
    "danger_hover": "#c65f68",
}


class GitPlugin:
    """
    Plugin para integração com Git.
    Responsável por monitorar o estado do repositório e realizar commits rápidos,
    além de oferecer um painel visual com ações rápidas (branch, pull, push, sync).
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
            if not output:
                return []

            items = []
            for line in output.splitlines():
                if len(line) >= 4:
                    code = line[:2]  # Ex: 'M ', 'A ', '??'
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
        colors = {"mod": COLORS["mod"], "add": COLORS["add"], "del": COLORS["del"]}
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
                if current_text.startswith("[") and "] " in current_text:
                    clean_text = current_text.split("] ", 1)[1]
                else:
                    clean_text = current_text

                if abs_path in status_map:
                    char, color = status_map[abs_path]
                    btn.configure(text=f"[{char}] {clean_text}", text_color=color)
                else:
                    btn.configure(text=clean_text, text_color=theme_fg)

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

    def create_branch(self, branch_name: str, checkout: bool = True) -> Tuple[bool, str]:
        """Cria uma nova branch. Se checkout=True, já troca para ela (git checkout -b)."""
        root = self.ctx.project_root
        if not root or not branch_name.strip():
            return False, "Nome de branch inválido."
        try:
            cmd = ["git", "checkout", "-b", branch_name.strip()] if checkout else ["git", "branch", branch_name.strip()]
            subprocess.run(cmd, cwd=root, check=True, capture_output=True, text=True)
            self.async_update_status()
            return True, f"Branch '{branch_name.strip()}' criada com sucesso."
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() if e.stderr else str(e)

    def git_push(self, on_done=None):
        root = self.ctx.project_root
        if not root:
            return

        def task():
            try:
                subprocess.run(["git", "push"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Push concluído."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha no push.")
            self.async_update_status()
            if on_done:
                self.ctx.window.after(0, lambda: on_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()

    def git_pull(self, on_done=None):
        root = self.ctx.project_root
        if not root:
            return

        def task():
            try:
                subprocess.run(["git", "pull"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Pull concluído."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha no pull.")
            self.async_update_status()
            if on_done:
                self.ctx.window.after(0, lambda: on_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()

    def git_sync(self, on_done=None):
        """Executa pull seguido de push (sincronização rápida)."""
        root = self.ctx.project_root
        if not root:
            return

        def task():
            try:
                subprocess.run(["git", "pull"], cwd=root, check=True, capture_output=True, text=True)
                subprocess.run(["git", "push"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Sincronização concluída."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha na sincronização.")
            self.async_update_status()
            if on_done:
                self.ctx.window.after(0, lambda: on_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()


    def quick_commit_ui(self):
        """Abre um painel flutuante com status, commit rápido e ações de branch/pull/push/sync."""
        if not self.ctx.project_root or not self.is_git_repo(self.ctx.project_root):
            return

        branch, _ = self.get_git_info()

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.title("󰊢 Git")
        dialog.geometry("480x620")
        dialog.minsize(440, 560)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.focus_set()

        header = ctk.CTkFrame(dialog, fg_color=COLORS["panel"], corner_radius=10)
        header.pack(fill="x", padx=16, pady=(16, 8))

        branch_label = ctk.CTkLabel(
            header, text=f"󰘬  {branch or '(sem branch)'}",
            font=("Segoe UI", 14, "bold"), text_color=COLORS["accent"]
        )
        branch_label.pack(side="left", padx=12, pady=10)

        def refresh_status_label():
            b, c = self.get_git_info()
            branch_label.configure(text=f"󰘬  {b or '(sem branch)'}" + (f"  ·  {c} alteração(ões)" if c else ""))

        refresh_btn = ctk.CTkButton(
            header, text="󰑐", width=32, height=28, font=("Segoe UI", 13),
            fg_color="transparent", hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: [refresh_status_label(), reload_file_list()]
        )
        refresh_btn.pack(side="right", padx=8, pady=8)

        toolbar = ctk.CTkFrame(dialog, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 8))
        toolbar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def set_toolbar_busy(busy: bool, msg: str = ""):
            state = "disabled" if busy else "normal"
            for b in (new_branch_btn, switch_branch_btn, pull_btn, push_btn, sync_btn):
                b.configure(state=state)
            if msg:
                feedback_label.configure(text=msg)

        def with_feedback(action_fn):
            def wrapped(*args, **kwargs):
                set_toolbar_busy(True, "󰔟  Executando...")
                def on_done(ok, msg):
                    set_toolbar_busy(False, ("󰄬  " if ok else "󰅙  ") + msg)
                    refresh_status_label()
                    reload_file_list()
                action_fn(on_done=on_done, *args, **kwargs)
            return wrapped

        new_branch_btn = ctk.CTkButton(
            toolbar, text="󰐕  Nova Branch", height=32, font=("Segoe UI", 11),
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: self._open_create_branch_dialog(dialog, on_created=lambda: [refresh_status_label(), reload_file_list()])
        )
        new_branch_btn.grid(row=0, column=0, padx=4, sticky="ew")

        switch_branch_btn = ctk.CTkButton(
            toolbar, text="󰲣  Trocar", height=32, font=("Segoe UI", 11),
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: self._open_switch_branch_dialog(dialog, on_switched=lambda: [refresh_status_label(), reload_file_list()])
        )
        switch_branch_btn.grid(row=0, column=1, padx=4, sticky="ew")

        pull_btn = ctk.CTkButton(
            toolbar, text="󰇚  Pull", height=32, font=("Segoe UI", 11),
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: with_feedback(self.git_pull)()
        )
        pull_btn.grid(row=0, column=2, padx=4, sticky="ew")

        push_btn = ctk.CTkButton(
            toolbar, text="󰊤  Push", height=32, font=("Segoe UI", 11),
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: with_feedback(self.git_push)()
        )
        push_btn.grid(row=1, column=0, columnspan=2, padx=4, pady=(6, 0), sticky="ew")

        sync_btn = ctk.CTkButton(
            toolbar, text="󰓦  Sincronizar (Pull + Push)", height=32, font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#1e2127",
            command=lambda: with_feedback(self.git_sync)()
        )
        sync_btn.grid(row=1, column=2, columnspan=2, padx=4, pady=(6, 0), sticky="ew")

        feedback_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 10), text_color=COLORS["text_dim"])
        feedback_label.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(
            dialog, text="Arquivos Alterados", font=("Segoe UI", 12, "bold"), text_color=COLORS["text"]
        ).pack(pady=(6, 0), padx=20, anchor="w")

        text_area = ctk.CTkTextbox(
            dialog, height=170, font=("Consolas", 11),
            fg_color=COLORS["panel_alt"], corner_radius=8, border_width=1, border_color=COLORS["border"]
        )
        text_area.pack(fill="x", padx=20, pady=6)

        text_area._textbox.tag_configure("mod", foreground=COLORS["mod"])
        text_area._textbox.tag_configure("add", foreground=COLORS["add"])
        text_area._textbox.tag_configure("del", foreground=COLORS["del"])

        def reload_file_list():
            text_area.configure(state="normal")
            text_area.delete("1.0", "end")
            status_data = self.get_status_data()
            if not status_data:
                text_area.insert("end", "  Nenhuma alteração pendente.")
            else:
                for code, path in status_data:
                    tag = None
                    if 'M' in code or 'R' in code: tag = "mod"
                    elif 'A' in code or '?' in code: tag = "add"
                    elif 'D' in code: tag = "del"

                    text_area._textbox.insert("end", f"{code} ", tag)
                    text_area._textbox.insert("end", f"{path}\n")
            text_area.configure(state="disabled")

        reload_file_list()


        ctk.CTkLabel(
            dialog, text="Mensagem de Commit", font=("Segoe UI", 12, "bold"), text_color=COLORS["text"]
        ).pack(pady=(10, 0), padx=20, anchor="w")

        entry = ctk.CTkEntry(
            dialog, placeholder_text="O que você mudou?",
            fg_color=COLORS["panel_alt"], border_color=COLORS["border"], corner_radius=8
        )
        entry.pack(fill="x", padx=20, pady=6)
        entry.focus_set()

        def execute_commit():
            msg = entry.get()
            if not msg:
                return
            commit_btn.configure(state="disabled", text="󰊢  Commitando...")

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
                    self.ctx.window.after(0, lambda: commit_btn.configure(state="normal", text="󰊢  Commit"))

            threading.Thread(target=task, daemon=True).start()

        commit_btn = ctk.CTkButton(
            dialog, text="󰊢  Commit", height=36, font=("Segoe UI", 12, "bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#1e2127",
            command=execute_commit
        )
        commit_btn.pack(pady=16, padx=20, fill="x")

        ctk.CTkLabel(
            dialog, text="Dica: [ENTER] confirma commit  ·  [ESC] fecha",
            font=("Segoe UI", 10), text_color=COLORS["text_dim"]
        ).pack(pady=(0, 12))

        dialog.bind("<Return>", lambda e: execute_commit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _open_create_branch_dialog(self, parent, on_created=None):
        """Pequeno diálogo para criar (e trocar para) uma nova branch."""
        popup = ctk.CTkToplevel(parent)
        popup.title("󰐕 Nova Branch")
        popup.geometry("360x180")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=COLORS["bg"])
        popup.focus_set()

        ctk.CTkLabel(
            popup, text="Nome da nova branch", font=("Segoe UI", 12, "bold"), text_color=COLORS["text"]
        ).pack(pady=(20, 4), padx=20, anchor="w")

        entry = ctk.CTkEntry(
            popup, placeholder_text="feature/minha-branch",
            fg_color=COLORS["panel_alt"], border_color=COLORS["border"], corner_radius=8
        )
        entry.pack(fill="x", padx=20, pady=4)
        entry.focus_set()

        feedback = ctk.CTkLabel(popup, text="", font=("Segoe UI", 10), text_color=COLORS["danger"])
        feedback.pack(padx=20, anchor="w")

        def confirm():
            name = entry.get().strip()
            if not name:
                feedback.configure(text="Digite um nome válido.")
                return
            ok, msg = self.create_branch(name, checkout=True)
            if ok:
                popup.destroy()
                if on_created:
                    on_created()
            else:
                feedback.configure(text=msg[:80])

        btn = ctk.CTkButton(
            popup, text="Criar e Trocar", height=32,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#1e2127",
            command=confirm
        )
        btn.pack(pady=16, padx=20, fill="x")

        popup.bind("<Return>", lambda e: confirm())
        popup.bind("<Escape>", lambda e: popup.destroy())

    def _open_switch_branch_dialog(self, parent, on_switched=None):
        """Pequeno diálogo para escolher e trocar de branch existente."""
        branches = self.get_branches()
        if not branches:
            return

        popup = ctk.CTkToplevel(parent)
        popup.title("󰲣 Trocar Branch")
        popup.geometry("360x220")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=COLORS["bg"])
        popup.focus_set()

        ctk.CTkLabel(
            popup, text="Selecione a branch", font=("Segoe UI", 12, "bold"), text_color=COLORS["text"]
        ).pack(pady=(20, 4), padx=20, anchor="w")

        current_branch, _ = self.get_git_info()
        combo = ctk.CTkComboBox(
            popup, values=branches, fg_color=COLORS["panel_alt"],
            border_color=COLORS["border"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"]
        )
        combo.set(current_branch if current_branch in branches else branches[0])
        combo.pack(fill="x", padx=20, pady=4)

        feedback = ctk.CTkLabel(popup, text="", font=("Segoe UI", 10), text_color=COLORS["text_dim"])
        feedback.pack(padx=20, anchor="w")

        def confirm():
            target = combo.get().strip()
            if not target:
                return
            feedback.configure(text="󰔟  Trocando...")
            popup.update_idletasks()
            self.switch_branch(target)
            popup.destroy()
            if on_switched:
                on_switched()

        btn = ctk.CTkButton(
            popup, text="Trocar", height=32,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#1e2127",
            command=confirm
        )
        btn.pack(pady=16, padx=20, fill="x")

        popup.bind("<Return>", lambda e: confirm())
        popup.bind("<Escape>", lambda e: popup.destroy())