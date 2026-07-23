import subprocess
import threading
import os
import tkinter as tk
import tkinter.font as tkfont
from typing import Optional, Tuple, List
import customtkinter as ctk
from core.src.app_context import AppContext


# Paleta de cores (tema Atom/OneDark) usada em todo o painel visual
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

# Cores das "raias" (lanes) do grafo de commits, cicladas por coluna/branch
GRAPH_COLORS = ["#e06c75", "#61afef", "#56b6c2", "#c678dd", "#e5c07b", "#98c379", "#d19a66"]


class GitPlugin:
    """
    Plugin para integração com Git.
    Responsável por monitorar o estado do repositório e realizar commits rápidos,
    além de oferecer um painel visual com ações rápidas (branch, pull, push, sync).
    """
    def __init__(self):
        self.ctx = AppContext()

    # ------------------------------------------------------------------ #
    # Consultas ao git
    # ------------------------------------------------------------------ #
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

    def get_commit_graph(self, limit: int = 80) -> List[dict]:
        """
        Retorna o histórico de commits já com a coluna (lane) real de cada um,
        calculada a partir dos hashes-pai de cada commit (mesma ideia usada por
        ferramentas como o Git Graph do VS Code) — não é mais um "chute" a partir
        do texto do `git log --graph`, é um layout de verdade.
        """
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            sep, rec = "\x1f", "\x1e"
            fmt = f"%H{sep}%h{sep}%an{sep}%ad{sep}%s{sep}%P{rec}"
            output = subprocess.check_output(
                ["git", "log", "--topo-order", f"-n{limit}",
                 f"--pretty=format:{fmt}", "--date=short"],
                cwd=root, stderr=subprocess.DEVNULL, text=True
            )
            raw = []
            for entry in output.split(rec):
                entry = entry.strip("\n")
                if not entry.strip():
                    continue
                parts = entry.split(sep)
                if len(parts) != 6:
                    continue
                full_hash, short_hash, author, date, msg, parents_str = parts
                parents = parents_str.split() if parents_str.strip() else []
                raw.append({
                    "full": full_hash, "hash": short_hash, "author": author,
                    "date": date, "message": msg, "parents": parents
                })
        except Exception:
            return []

        head_branch, _ = self.get_git_info()
        return self._layout_commit_graph(raw, head_branch)

    def _layout_commit_graph(self, raw_commits: List[dict], head_branch: str) -> List[dict]:
        """
        Layout clássico de grafo de commits: mantém uma lista de 'raias' (lanes),
        cada uma esperando pelo próximo hash que deve aparecer nela. Quando um
        commit aparece, ele ocupa a raia (ou raias, em caso de merge) que esperava
        por ele, libera o que não usa mais, e abre novas raias para pais extras
        (merge). Isso permite desenhar linhas retas/diagonais reais entre as linhas.
        """
        lanes: List[Optional[str]] = []
        result = []

        for c in raw_commits:
            h = c["full"]
            lanes_before = list(lanes)

            incoming_cols = [i for i, target in enumerate(lanes) if target == h]
            if incoming_cols:
                col = min(incoming_cols)
            else:
                col = next((i for i, t in enumerate(lanes) if t is None), None)
                if col is None:
                    col = len(lanes)
                    lanes.append(None)

            for i in incoming_cols:
                if i != col:
                    lanes[i] = None

            parents = c["parents"]
            outgoing_cols = []
            if parents:
                lanes[col] = parents[0]
                outgoing_cols.append(col)
                for p in parents[1:]:
                    existing = next((i for i, t in enumerate(lanes) if t == p), None)
                    if existing is not None:
                        outgoing_cols.append(existing)
                        continue
                    new_col = next((i for i, t in enumerate(lanes) if t is None), None)
                    if new_col is None:
                        new_col = len(lanes)
                        lanes.append(None)
                    lanes[new_col] = p
                    outgoing_cols.append(new_col)
            else:
                lanes[col] = None
            passthrough = [
                i for i, t in enumerate(lanes_before)
                if t is not None and i not in incoming_cols
            ]

            is_merge = len(parents) > 1
            result.append({
                "hash": c["hash"], "author": c["author"], "date": c["date"],
                "message": c["message"], "col": col,
                "incoming": [i for i in incoming_cols if i != col],
                "same_col_in": col in incoming_cols,
                "outgoing": [i for i in outgoing_cols if i != col],
                "same_col_out": col in outgoing_cols,
                "passthrough": passthrough,
                "is_merge": is_merge,
                "is_head": len(result) == 0,
            })

        return result

    def get_commit_log(self, limit: int = 60) -> List[dict]:
        """Retorna o histórico de commits (hash curto, autor, data, mensagem)."""
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            fmt = "%h\x1f%an\x1f%ad\x1f%s\x1e"
            output = subprocess.check_output(
                ["git", "log", f"-n{limit}", f"--pretty=format:{fmt}", "--date=short"],
                cwd=root, stderr=subprocess.DEVNULL, text=True
            )
            commits = []
            for entry in output.split("\x1e"):
                entry = entry.strip()
                if not entry:
                    continue
                parts = entry.split("\x1f")
                if len(parts) == 4:
                    h, author, date, msg = parts
                    commits.append({"hash": h, "author": author, "date": date, "message": msg})
            return commits
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Ações sobre arquivos / staging
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Branches
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Push / Pull / Sync
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Painel visual (Quick Commit + ações rápidas)
    # ------------------------------------------------------------------ #
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

        # ---------------------------------------------------------- #
        # Cabeçalho: branch atual + seletor de branch + refresh
        # ---------------------------------------------------------- #
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

        # ---------------------------------------------------------- #
        # Barra de ações rápidas: Nova Branch / Trocar Branch / Pull / Push / Sync
        # ---------------------------------------------------------- #
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

        history_btn = ctk.CTkButton(
            toolbar, text="󰋚  Histórico", height=32, font=("Segoe UI", 11),
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: self._open_commit_log_dialog(dialog)
        )
        history_btn.grid(row=0, column=3, padx=4, sticky="ew")

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

        # ---------------------------------------------------------- #
        # Lista de arquivos alterados
        # ---------------------------------------------------------- #
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

        # ---------------------------------------------------------- #
        # Commit rápido
        # ---------------------------------------------------------- #
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

    # ------------------------------------------------------------------ #
    # Diálogos auxiliares (branch)
    # ------------------------------------------------------------------ #
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

    def _open_commit_log_dialog(self, parent):
        """Painel de histórico de commits com grafo real (colunas calculadas a partir
        dos hashes-pai), desenhado em um único Canvas — estilo compacto parecido com
        a extensão Git Graph do VS Code: raia + ponto, uma linha por commit, HEAD
        destacado com badge da branch."""
        ROW_H = 26
        GRAPH_PAD = 14
        MIN_TEXT_W = 380

        popup = ctk.CTkToplevel(parent)
        popup.title("󰋚 Histórico de Commits")
        popup.geometry("620x600")
        popup.minsize(460, 380)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=COLORS["bg"])
        popup.focus_set()

        header = ctk.CTkFrame(popup, fg_color=COLORS["panel"], corner_radius=10)
        header.pack(fill="x", padx=16, pady=(16, 8))

        branch, _ = self.get_git_info()
        ctk.CTkLabel(
            header, text=f"󰘬  {branch or '(sem branch)'}",
            font=("Segoe UI", 13, "bold"), text_color=COLORS["accent"]
        ).pack(side="left", padx=12, pady=8)

        refresh_btn = ctk.CTkButton(
            header, text="󰑐", width=32, height=28, font=("Segoe UI", 13),
            fg_color="transparent", hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=lambda: reload_log()
        )
        refresh_btn.pack(side="right", padx=8, pady=8)

        # ------------------------------------------------------------ #
        # Área do grafo: um único Canvas (garante linhas contínuas e
        # alinhamento perfeito entre linhas, sem gaps de frames separados)
        # ------------------------------------------------------------ #
        canvas_frame = ctk.CTkFrame(popup, fg_color=COLORS["panel_alt"], corner_radius=10)
        canvas_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        graph_canvas = tk.Canvas(canvas_frame, bg=COLORS["panel_alt"], highlightthickness=0)
        graph_canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)

        vscroll = ctk.CTkScrollbar(canvas_frame, orientation="vertical", command=graph_canvas.yview)
        vscroll.grid(row=0, column=1, sticky="ns", pady=2, padx=(0, 2))
        graph_canvas.configure(yscrollcommand=vscroll.set)

        hscroll = ctk.CTkScrollbar(canvas_frame, orientation="horizontal", command=graph_canvas.xview)
        hscroll.grid(row=1, column=0, sticky="ew", padx=(2, 0))
        graph_canvas.configure(xscrollcommand=hscroll.set)

        def _on_mousewheel(event):
            graph_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_shift_mousewheel(event):
            graph_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_e):
            graph_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            graph_canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)

        def _unbind_wheel(_e):
            graph_canvas.unbind_all("<MouseWheel>")
            graph_canvas.unbind_all("<Shift-MouseWheel>")

        graph_canvas.bind("<Enter>", _bind_wheel)
        graph_canvas.bind("<Leave>", _unbind_wheel)

        state = {"commits": None}
        msg_font = tkfont.Font(family="Segoe UI", size=11)
        dim_font = tkfont.Font(family="Segoe UI", size=9)

        def lane_color(col: int) -> str:
            return GRAPH_COLORS[col % len(GRAPH_COLORS)]

        def draw(commits):
            graph_canvas.delete("all")
            visible_w = max(graph_canvas.winfo_width(), 420)

            if not commits:
                graph_canvas.create_text(
                    20, 24, anchor="w", text="Nenhum commit encontrado neste repositório.",
                    fill=COLORS["text_dim"], font=("Segoe UI", 11)
                )
                graph_canvas.configure(scrollregion=(0, 0, visible_w, 60))
                return

            max_col = max(
                max([c["col"]] + c["incoming"] + c["outgoing"] + c["passthrough"], default=0)
                for c in commits
            )

            # colunas mais estreitas quando há muitas branches, pra caber mais raias
            # visíveis antes de precisar rolar horizontalmente
            if max_col <= 6:
                col_w = 16
            elif max_col <= 12:
                col_w = 12
            else:
                col_w = 9

            graph_w = GRAPH_PAD + max_col * col_w + 22
            tx = graph_w
            content_w = max(visible_w, graph_w + MIN_TEXT_W)
            total_h = len(commits) * ROW_H

            def lane_x(col: int) -> float:
                return GRAPH_PAD + col * col_w

            for i, c in enumerate(commits):
                y0, y1 = i * ROW_H, (i + 1) * ROW_H
                yc = y0 + ROW_H / 2
                col_x = lane_x(c["col"])
                color = lane_color(c["col"])

                if c["is_head"]:
                    graph_canvas.create_rectangle(
                        0, y0, content_w, y1, fill="#2c3a4d", width=0
                    )
                elif i % 2 == 1:
                    graph_canvas.create_rectangle(
                        0, y0, content_w, y1, fill=COLORS["panel"], width=0
                    )

                # raias que só passam retas por esta linha (sem relação com o commit)
                for pcol in c["passthrough"]:
                    px = lane_x(pcol)
                    graph_canvas.create_line(px, y0, px, y1, fill=lane_color(pcol), width=2)

                # topo: liga com a linha de cima (reta se mesma coluna, diagonal se convergindo)
                if c["same_col_in"]:
                    graph_canvas.create_line(col_x, y0, col_x, yc, fill=color, width=2)
                for icol in c["incoming"]:
                    ix = lane_x(icol)
                    graph_canvas.create_line(ix, y0, col_x, yc, fill=lane_color(icol), width=2)

                # baixo: liga com a linha de baixo (reta se mesma coluna, diagonal se divergindo/merge)
                if c["same_col_out"]:
                    graph_canvas.create_line(col_x, yc, col_x, y1, fill=color, width=2)
                for ocol in c["outgoing"]:
                    ox = lane_x(ocol)
                    graph_canvas.create_line(col_x, yc, ox, y1, fill=color, width=2)

                r = 5 if c["is_merge"] else (4 if col_w >= 12 else 3)
                graph_canvas.create_oval(
                    col_x - r, yc - r, col_x + r, yc + r,
                    fill=color, outline=COLORS["bg"], width=2
                )

                # texto: uma linha só (mensagem + autor), compacto, estilo Git Graph
                msg = c["message"]
                avail_px = content_w - tx - 70
                while msg and msg_font.measure(msg) > avail_px:
                    msg = msg[:-1]
                if msg != c["message"]:
                    msg = msg[:-1] + "…"

                msg_color = "#ffffff" if c["is_head"] else COLORS["text"]
                msg_weight = "bold" if c["is_head"] else "normal"
                row_font = tkfont.Font(family="Segoe UI", size=11, weight=msg_weight)

                graph_canvas.create_text(
                    tx, yc, anchor="w", text=msg, fill=msg_color, font=row_font
                )
                msg_w = row_font.measure(msg)

                author_x = tx + msg_w + 12
                graph_canvas.create_text(
                    author_x, yc, anchor="w", text=c["author"],
                    fill=COLORS["text_dim"], font=dim_font
                )

                graph_canvas.create_text(
                    content_w - 14, yc, anchor="e", text=c["hash"],
                    fill=COLORS["text_dim"], font=("Consolas", 9)
                )

                if c["is_head"] and branch:
                    label = branch if len(branch) <= 18 else branch[:16] + "…"
                    pill_w = tkfont.Font(family="Segoe UI", size=9, weight="bold").measure(label) + 16
                    pill_x = author_x + dim_font.measure(c["author"]) + 10
                    graph_canvas.create_rectangle(
                        pill_x, yc - 9, pill_x + pill_w, yc + 9,
                        fill=COLORS["accent"], outline="", width=0
                    )
                    graph_canvas.create_text(
                        pill_x + pill_w / 2, yc, text=label,
                        fill="#1e2127", font=("Segoe UI", 9, "bold")
                    )

            graph_canvas.configure(scrollregion=(0, 0, content_w, total_h))

        def reload_log():
            """Busca o log de novo no git (usado no botão de refresh / abertura inicial)."""
            state["commits"] = self.get_commit_graph()
            draw(state["commits"])

        def redraw_only(_event=None):
            """Apenas re-desenha com os dados já buscados (usado em redimensionamento)."""
            if state["commits"] is not None:
                draw(state["commits"])

        # a primeira renderização precisa esperar o Canvas ter largura real
        popup.after(30, reload_log)
        graph_canvas.bind("<Configure>", redraw_only)

        close_btn = ctk.CTkButton(
            popup, text="Fechar", height=32,
            fg_color=COLORS["panel"], hover_color=COLORS["panel_alt"], text_color=COLORS["text"],
            command=popup.destroy
        )
        close_btn.pack(pady=(0, 16), padx=20, fill="x")

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