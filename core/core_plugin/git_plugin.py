#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import json
import os
import subprocess
import threading
from typing import List, Optional, Tuple

from core.src.app_context import AppContext
from core.src.session import SessionManager
from core.src.theme_manager import ThemeManager


class GitPlugin:
    _TABS = {
        "changes": "Alterações",
        "history": "Histórico",
        "branches": "Branches",
        "remote": "Remoto",
    }

    def __init__(self):
        self.ctx = AppContext()
        self._panel = None
        self._load_theme()

    def _load_theme(self):
        self.colors = {
            "bg": "#1e2127", "panel": "#282c34", "panel_alt": "#21252b",
            "border": "#3a3f4b", "text": "#cccccc", "text_dim": "#7f848e",
            "accent": "#61afef", "accent_hover": "#4d94d6", "mod": "#e5c07b",
            "add": "#98c379", "del": "#e06c75", "danger": "#e06c75",
            "danger_hover": "#c65f68", "on_accent": "#14181f",
        }
        self.graph_colors = ["#e06c75", "#61afef", "#56b6c2", "#c678dd",
                             "#e5c07b", "#98c379", "#d19a66"]

        try:
            pref_path = SessionManager.get_pref_path()

            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)

                theme_name = prefs.get("selected_theme")
                if theme_name:
                    theme_path = ThemeManager.resolve_theme_path(theme_name)
                    if os.path.exists(theme_path):
                        with open(theme_path, "r", encoding="utf-8") as t:
                            theme = json.load(t)

                        editor = theme.get("editor", {})
                        sidebar = theme.get("sidebar", {})
                        status_bar = theme.get("status_bar", {})
                        syntax = theme.get("syntax", {})

                        self.colors["bg"] = editor.get("bg", self.colors["bg"])
                        self.colors["panel"] = status_bar.get("bg", self.colors["panel"])
                        self.colors["panel_alt"] = sidebar.get("bg", self.colors["panel_alt"])
                        self.colors["border"] = sidebar.get("label", self.colors["border"])
                        self.colors["text"] = editor.get("fg", self.colors["text"])
                        self.colors["text_dim"] = sidebar.get("fg", self.colors["text_dim"])
                        self.colors["accent"] = syntax.get("builtin", self.colors["accent"])
                        self.colors["accent_hover"] = syntax.get("keyword", self.colors["accent_hover"])
                        self.colors["mod"] = syntax.get("string", self.colors["mod"])
                        self.colors["add"] = syntax.get("definition", self.colors["add"])
                        self.colors["del"] = syntax.get("keyword", self.colors["del"])
                        self.colors["danger"] = syntax.get("keyword", self.colors["danger"])
                        self.colors["danger_hover"] = syntax.get("comment", self.colors["danger_hover"])

                        self.graph_colors = [
                            syntax.get("keyword", self.graph_colors[0]),
                            syntax.get("builtin", self.graph_colors[1]),
                            syntax.get("string", self.graph_colors[2]),
                            syntax.get("number", self.graph_colors[3]),
                            syntax.get("definition", self.graph_colors[4]),
                        ]
        except Exception as e:
            print(f"Erro ao carregar as cores do tema: {e}")

    @staticmethod
    def _rel(root: str, path: str) -> str:
        """Converte caminhos absolutos dentro do repositório em relativos."""
        try:
            if os.path.isabs(path):
                rel = os.path.relpath(path, root)
                if not rel.startswith(".."):
                    return rel
            return path
        except Exception:
            return path

    def _git(self, args: List[str], root: Optional[str] = None) -> Tuple[bool, str]:
        """Roda ``git <args>`` e devolve ``(ok, saída)``. Nunca lança exceção."""
        root = root or self.ctx.project_root
        if not root:
            return False, "Nenhuma pasta aberta."
        try:
            proc = subprocess.run(["git", *args], cwd=root,
                                  capture_output=True, text=True)
        except FileNotFoundError:
            return False, "Git não encontrado no sistema."
        except OSError as e:
            return False, str(e)

        out = (proc.stdout or "").rstrip("\n\r")
        err = (proc.stderr or "").rstrip("\n\r")
        if proc.returncode != 0:
            return False, (err or out or f"git {' '.join(args)} falhou.").strip()
        return True, out

    def is_git_repo(self, path: str) -> bool:
        if not path:
            return False
        try:
            subprocess.check_output(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False

    def is_repo(self) -> bool:
        """True quando o projeto aberto é um repositório Git."""
        return self.is_git_repo(self.ctx.project_root)

    def get_git_info(self) -> Tuple[str, int]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return "", 0
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], cwd=root,
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            status = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root,
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            num_changes = len(status.splitlines()) if status else 0
            return branch, num_changes
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return "", 0

    def get_status_data(self) -> List[Tuple[str, str]]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:

            output = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root,
                stderr=subprocess.DEVNULL, text=True,
            )
            items = []
            for line in output.splitlines():
                if len(line) < 4:
                    continue
                code = line[:2]
                path = line[3:].strip()
                if " -> " in path:          
                    path = path.split(" -> ", 1)[1].strip()
                items.append((code, path.strip('"')))
            return items
        except Exception:
            return []

    def get_diff(self, path: str = None) -> str:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return ""
        try:
            cmd = ["git", "diff"]
            if path:
                cmd += ["--", self._rel(root, path)]
            return subprocess.check_output(cmd, cwd=root, stderr=subprocess.STDOUT,
                                           text=True)
        except Exception as e:
            return str(e)

    def get_file_diff(self, path: str, staged: bool = False) -> str:
        """Diff de um único arquivo (index ou working tree)."""
        root = self.ctx.project_root
        if not root or not path or not self.is_git_repo(root):
            return ""
        cmd = ["diff"]
        if staged:
            cmd.append("--cached")
        cmd += ["--", self._rel(root, path)]
        ok, out = self._git(cmd, root)
        return out if ok else ""

    # ── status assíncrono (barra de status + sidebar) ───────────────────

    def decorate_sidebar(self):
        window = self.ctx.window
        if window is None or not self.ctx.sidebar or not hasattr(self.ctx.sidebar, "item_widgets"):
            return

        root = self.ctx.project_root
        status_data = self.get_status_data()
        colors = {"mod": self.colors["mod"], "add": self.colors["add"],
                  "del": self.colors["del"]}
        theme_fg = self.ctx.theme.get("sidebar", {}).get("fg", self.colors["text"])

        status_map = {}
        for code, rel_path in status_data:
            abs_path = os.path.abspath(os.path.join(root, rel_path))
            char = ""
            color = theme_fg
            if "M" in code:
                char, color = "M", colors["mod"]
            elif "A" in code or "?" in code:
                char, color = "A", colors["add"]
            elif "D" in code:
                char, color = "D", colors["del"]
            elif "R" in code:
                char, color = "R", colors["mod"]

            if char:
                status_map[abs_path] = (char, color)

        def update_ui():
            try:
                items = list(self.ctx.sidebar.item_widgets.items())
            except Exception:
                return
            for path, btn in items:
                try:
                    abs_path = os.path.abspath(path)
                    current_text = btn.cget("text")
                    if current_text.startswith("[") and "] " in current_text:
                        clean_text = current_text.split("] ", 1)[1]
                    else:
                        clean_text = current_text

                    if abs_path in status_map:
                        char, color = status_map[abs_path]
                        btn.configure(text=f"[{char}] {clean_text}", text_color=color)
                    else:
                        btn.configure(text=clean_text, text_color=theme_fg)
                except Exception:
                    continue

        self._ui_call(0, update_ui)

    def async_update_status(self):
        window = self.ctx.window
        if window is None:
            return

        def task():
            branch, changes = self.get_git_info()
            root = self.ctx.project_root
            is_repo = self.is_git_repo(root) if root else False

            if self.ctx.status_bar:
                if branch:
                    status_str = f"Git: {branch}" + (f" ({changes})" if changes > 0 else "")
                    self._ui_call(0, lambda: self.ctx.status_bar.update_git_ui(status_str, changes > 0))
                elif is_repo:
                    self._ui_call(0, lambda: self.ctx.status_bar.update_git_ui("Git: (repo)", False))
                else:
                    self._ui_call(0, lambda: self.ctx.status_bar.update_git_ui("", False))

            if is_repo:
                self._ui_call(50, self.decorate_sidebar)

        threading.Thread(target=task, daemon=True).start()

    def _ui_call(self, delay: int, fn):
        window = self.ctx.window
        if window is None:
            return
        try:
            window.after(delay, fn)
        except Exception:
            pass

    def _notify_panel(self):
        panel = self._panel
        if panel is None:
            return
        try:
            if panel.win.winfo_exists():
                panel.win.after(0, panel.refresh)
        except Exception:
            self._panel = None

    # ── histórico ───────────────────────────────────────────────────────

    def get_commit_graph(self, limit: int = 80) -> List[dict]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            sep, rec = "\x1f", "\x1e"
            fmt = f"%H{sep}%h{sep}%an{sep}%ad{sep}%s{sep}%P{rec}"
            output = subprocess.check_output(
                ["git", "log", "--topo-order", f"-n{limit}",
                 f"--pretty=format:{fmt}", "--date=short"],
                cwd=root, stderr=subprocess.DEVNULL, text=True,
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
                    "date": date, "message": msg, "parents": parents,
                })
        except Exception:
            return []

        head_branch, _ = self.get_git_info()
        return self._layout_commit_graph(raw, head_branch)

    def _layout_commit_graph(self, raw_commits: List[dict], head_branch: str) -> List[dict]:
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

            passthrough = [i for i, t in enumerate(lanes_before)
                           if t is not None and i not in incoming_cols]
            is_merge = len(parents) > 1

            result.append({
                "full": c["full"], "hash": c["hash"], "author": c["author"],
                "date": c["date"], "message": c["message"], "col": col,
                "incoming": [i for i in incoming_cols if i != col],
                "same_col_in": col in incoming_cols,
                "outgoing": [i for i in outgoing_cols if i != col],
                "same_col_out": col in outgoing_cols,
                "passthrough": passthrough, "is_merge": is_merge,
                "is_head": len(result) == 0,
            })
        return result

    def stage_file(self, path: str) -> Tuple[bool, str]:
        root = self.ctx.project_root
        if not root:
            return False, "Nenhuma pasta aberta."
        ok, msg = self._git(["add", "--", self._rel(root, path)], root)
        self.async_update_status()
        self._notify_panel()
        return ok, msg

    def unstage_file(self, path: str) -> Tuple[bool, str]:
        root = self.ctx.project_root
        if not root:
            return False, "Nenhuma pasta aberta."
        ok, msg = self._git(["reset", "-q", "HEAD", "--", self._rel(root, path)], root)
        self.async_update_status()
        self._notify_panel()
        return ok, msg

    def stage_all(self) -> Tuple[bool, str]:
        ok, msg = self._git(["add", "-A"])
        self.async_update_status()
        self._notify_panel()
        return ok, ("Tudo staged." if ok else msg)

    def unstage_all(self) -> Tuple[bool, str]:
        ok, msg = self._git(["reset", "-q", "HEAD"])
        self.async_update_status()
        self._notify_panel()
        return ok, ("Nada staged." if ok else msg)

    def commit(self, message: str) -> Tuple[bool, str]:
        """Cria um commit com a mensagem informada."""
        message = (message or "").strip()
        if not message:
            return False, "Mensagem de commit vazia."
        ok, out = self._git(["commit", "-m", message])
        if not ok:
            return False, out
        self.async_update_status()
        self._notify_panel()
        return True, "Commit realizado."

    def get_branches(self) -> List[str]:
        return [b["name"] for b in self.get_branch_details()]

    def get_branch_details(self) -> List[dict]:
        """Lista as locais com hash, data, última mensagem e flag `current`."""
        ok, out = self._git([
            "for-each-ref", "--sort=-committerdate",
            "--format=%(HEAD)%09%(refname:short)%09%(objectname:short)"
            "%09%(committerdate:short)%09%(contents:subject)",
            "refs/heads",
        ])
        if not ok:
            return []
        branches = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            head_flag, name, short, date = parts[0], parts[1], parts[2], parts[3]
            subject = parts[4] if len(parts) > 4 else ""
            branches.append({
                "name": name, "hash": short, "date": date, "subject": subject,
                "current": head_flag.strip() == "*",
            })
        return branches

    def switch_branch(self, branch_name: str) -> Tuple[bool, str]:
        if not branch_name:
            return False, "Nenhuma branch informada."
        ok, msg = self._git(["checkout", branch_name])
        self.async_update_status()
        self._notify_panel()
        return ok, ("Branch alterada." if ok else msg)

    def create_branch(self, branch_name: str, checkout: bool = True) -> Tuple[bool, str]:
        branch_name = (branch_name or "").strip()
        if not branch_name:
            return False, "Nome de branch inválido."
        args = ["checkout", "-b", branch_name] if checkout else ["branch", branch_name]
        ok, msg = self._git(args)
        self.async_update_status()
        self._notify_panel()
        if not ok:
            return False, msg
        return True, f"Branch '{branch_name}' criada."

    def delete_branch(self, branch_name: str, force: bool = False) -> Tuple[bool, str]:
        if not branch_name:
            return False, "Nenhuma branch informada."
        ok, msg = self._git(["branch", "-D" if force else "-d", branch_name])
        self.async_update_status()
        self._notify_panel()
        if ok:
            return True, f"Branch '{branch_name}' excluída."
        if not force and "not fully merged" in msg:
            return False, "Branch não mesclada: use a exclusão forçada."
        return False, msg

    def get_remote_info(self) -> Optional[dict]:
        ok, out = self._git(["remote", "-v"])
        if not ok or not out:
            return None
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "(fetch)":
                return {"name": parts[0], "url": parts[2] if len(parts) > 2 else ""}
            if len(parts) >= 2:
                return {"name": parts[0], "url": parts[1]}
        return None

    def get_upstream_status(self) -> Optional[Tuple[int, int]]:
        """Devolve ``(ahead, behind)`` em relação ao upstream — ou None."""
        ok, out = self._git(["rev-list", "--left-right", "--count", "@{u}...HEAD"])
        if not ok or not out:
            return None
        parts = out.split()
        if len(parts) != 2:
            return None
        try:
            behind, ahead = int(parts[0]), int(parts[1])
        except ValueError:
            return None
        return ahead, behind

    def _remote_op(self, args: List[str], success: str, on_done=None):
        def task():
            ok, out = self._git(args)
            self.async_update_status()
            msg = success if ok else out
            if on_done:
                self._ui_call(0, lambda: on_done(ok, msg))

        threading.Thread(target=task, daemon=True).start()

    def git_push(self, on_done=None):
        self._remote_op(["push"], "Push concluído.", on_done)

    def git_pull(self, on_done=None):
        self._remote_op(["pull"], "Pull concluído.", on_done)

    def git_sync(self, on_done=None):
        def task():
            ok, out = self._git(["pull"])
            if not ok:
                self._ui_call(0, lambda m=out: on_done(False, m) if on_done else None)
                self.async_update_status()
                return
            ok, out = self._git(["push"])
            msg = "Sincronização concluída." if ok else out
            self.async_update_status()
            if on_done:
                self._ui_call(0, lambda m=msg, o=ok: on_done(o, m))

        threading.Thread(target=task, daemon=True).start()

    def open_panel(self, tab: str = "changes", file_path: Optional[str] = None):
        """Abre — ou reaproveita — a interface única do Git.

        Retorna o ``GitPanel`` aberto ou ``None`` quando a interface não pôde
        ser criada (aí apenas o Git fica indisponível; o editor não é afetado).
        """
        window = self.ctx.window
        if window is None:
            return None

        panel = self._panel
        if panel is not None:
            try:
                if panel.win.winfo_exists():
                    if file_path:
                        panel.select_file(file_path)
                    else:
                        panel.show_tab(self._TABS.get(tab, tab))
                    panel.refresh()
                    panel.win.lift()
                    panel.win.focus_force()
                    return panel
            except Exception:
                self._panel = None

        try:
            self._load_theme()
            from core.core_plugin.git_ui import GitPanel

            panel = GitPanel(self, window)
            self._panel = panel
            if file_path:
                panel.select_file(file_path)
            else:
                panel.show_tab(self._TABS.get(tab, tab))
            return panel
        except Exception as e:
            self._panel = None
            print(f"[GIT] Falha ao abrir a interface: {e}")
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass
            return None

    def quick_commit_ui(self):
        """Compat: abre a interface única na aba de alterações."""
        return self.open_panel("changes")

    def open_diff(self, path: str):
        """Compat: abre a interface única mostrando o diff de `path`."""
        return self.open_panel(file_path=path)
