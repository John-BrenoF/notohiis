#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import json
import subprocess
import threading
import os
import tkinter as tk
import tkinter.font as tkfont
from typing import Optional, Tuple, List
import customtkinter as ctk
from core.src.app_context import AppContext

class GitPlugin:
    def __init__(self):
        self.ctx = AppContext()
        self._load_theme()

    def _load_theme(self):
        self.colors = {
            "bg": "#1e2127", "panel": "#282c34", "panel_alt": "#21252b",
            "border": "#3a3f4b", "text": "#cccccc", "text_dim": "#7f848e",
            "accent": "#61afef", "accent_hover": "#4d94d6", "mod": "#e5c07b",
            "add": "#98c379", "del": "#e06c75", "danger": "#e06c75", "danger_hover": "#c65f68"
        }
        self.graph_colors = ["#e06c75", "#61afef", "#56b6c2", "#c678dd", "#e5c07b", "#98c379", "#d19a66"]

        try:
            base_dir = os.getcwd()
            pref_path = os.path.join(base_dir, "ui", "preferencias", "preferecia.json")
            
            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                
                theme_name = prefs.get("selected_theme")
                if theme_name:
                    theme_path = os.path.join(base_dir, "ui", "estilo", f"{theme_name}.json")
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
                                syntax.get("definition", self.graph_colors[4])
                            ]
        except Exception as e:
            print(f"Erro ao carregar as cores do tema: {e}")

    def is_git_repo(self, path: str) -> bool:
        try:
            subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def get_git_info(self) -> Tuple[str, int]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return "", 0
        try:
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            num_changes = len(status.splitlines()) if status else 0
            return branch, num_changes
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "", 0

    def get_status_data(self) -> List[Tuple[str, str]]:
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            output = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
            if not output:
                return []
            items = []
            for line in output.splitlines():
                if len(line) >= 4:
                    code = line[:2]
                    path = line[3:].strip().strip('"')
                    items.append((code, path))
            return items
        except Exception:
            return []

    def decorate_sidebar(self):
        if not self.ctx.sidebar or not hasattr(self.ctx.sidebar, "item_widgets"):
            return

        root = self.ctx.project_root
        status_data = self.get_status_data()
        colors = {"mod": self.colors["mod"], "add": self.colors["add"], "del": self.colors["del"]}
        theme_fg = self.ctx.theme.get("sidebar", {}).get("fg", self.colors["text"])

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
            items = list(self.ctx.sidebar.item_widgets.items())
            for path, btn in items:
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

        self.ctx.window.after(0, update_ui)

    def async_update_status(self):
        def task():
            branch, changes = self.get_git_info()
            is_repo = self.is_git_repo(self.ctx.project_root) if self.ctx.project_root else False

            if self.ctx.status_bar:
                if branch:
                    status_str = f"Git: {branch}" + (f" ({changes})" if changes > 0 else "")
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui(status_str, changes > 0))
                elif is_repo:
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui("Git: (repo)", False))
                else:
                    self.ctx.window.after(0, lambda: self.ctx.status_bar.update_git_ui("", False))

            if is_repo:
                self.ctx.window.after(50, self.decorate_sidebar)

        threading.Thread(target=task, daemon=True).start()

    def get_diff(self, path: str = None) -> str:
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
        root = self.ctx.project_root
        if not root or not self.is_git_repo(root):
            return []
        try:
            sep, rec = "\x1f", "\x1e"
            fmt = f"%H{sep}%h{sep}%an{sep}%ad{sep}%s{sep}%P{rec}"
            output = subprocess.check_output(
                ["git", "log", "--topo-order", f"-n{limit}", f"--pretty=format:{fmt}", "--date=short"],
                cwd=root, stderr=subprocess.DEVNULL, text=True
            )
            raw = []
            for entry in output.split(rec):
                entry = entry.strip("\n")
                if not entry.strip(): continue
                parts = entry.split(sep)
                if len(parts) != 6: continue
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
                if i != col: lanes[i] = None

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
                
            passthrough = [i for i, t in enumerate(lanes_before) if t is not None and i not in incoming_cols]
            is_merge = len(parents) > 1
            
            result.append({
                "full": c["full"], "hash": c["hash"], "author": c["author"], "date": c["date"],
                "message": c["message"], "col": col,
                "incoming": [i for i in incoming_cols if i != col],
                "same_col_in": col in incoming_cols,
                "outgoing": [i for i in outgoing_cols if i != col],
                "same_col_out": col in outgoing_cols,
                "passthrough": passthrough, "is_merge": is_merge, "is_head": len(result) == 0,
            })
        return result

    def get_commit_log(self, limit: int = 60) -> List[dict]:
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
                if not entry: continue
                parts = entry.split("\x1f")
                if len(parts) == 4:
                    h, author, date, msg = parts
                    commits.append({"hash": h, "author": author, "date": date, "message": msg})
            return commits
        except Exception:
            return []

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
        root = self.ctx.project_root
        if not root or not branch_name.strip():
            return False, "Nome de branch inválido."
        try:
            cmd = ["git", "checkout", "-b", branch_name.strip()] if checkout else ["git", "branch", branch_name.strip()]
            subprocess.run(cmd, cwd=root, check=True, capture_output=True, text=True)
            self.async_update_status()
            return True, f"Branch '{branch_name.strip()}' criada."
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() if e.stderr else str(e)

    def git_push(self, on_done=None):
        root = self.ctx.project_root
        if not root: return
        def task():
            try:
                subprocess.run(["git", "push"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Push concluído."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha no push.")
            self.async_update_status()
            if on_done: self.ctx.window.after(0, lambda: on_done(ok, msg))
        threading.Thread(target=task, daemon=True).start()

    def git_pull(self, on_done=None):
        root = self.ctx.project_root
        if not root: return
        def task():
            try:
                subprocess.run(["git", "pull"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Pull concluído."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha no pull.")
            self.async_update_status()
            if on_done: self.ctx.window.after(0, lambda: on_done(ok, msg))
        threading.Thread(target=task, daemon=True).start()

    def git_sync(self, on_done=None):
        root = self.ctx.project_root
        if not root: return
        def task():
            try:
                subprocess.run(["git", "pull"], cwd=root, check=True, capture_output=True, text=True)
                subprocess.run(["git", "push"], cwd=root, check=True, capture_output=True, text=True)
                ok, msg = True, "Sync concluída."
            except subprocess.CalledProcessError as e:
                ok, msg = False, (e.stderr.strip() if e.stderr else "Falha na sync.")
            self.async_update_status()
            if on_done: self.ctx.window.after(0, lambda: on_done(ok, msg))
        threading.Thread(target=task, daemon=True).start()

    def quick_commit_ui(self):
        if not self.ctx.project_root or not self.is_git_repo(self.ctx.project_root):
            return

        branch, _ = self.get_git_info()

        dialog = ctk.CTkToplevel(self.ctx.window)
        dialog.title("Git")
        dialog.geometry("820x520")
        dialog.minsize(700, 420)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=self.colors["bg"])
        dialog.focus_set()

        sidebar = ctk.CTkFrame(dialog, fg_color=self.colors["panel"], width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main_area = ctk.CTkFrame(dialog, fg_color="transparent")
        main_area.pack(side="right", fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(sidebar, text="Local", font=("Segoe UI", 11, "bold"), text_color=self.colors["text_dim"]).pack(anchor="w", padx=16, pady=(16, 4))

        btn_style = {"height": 30, "font": ("Segoe UI", 11), "fg_color": "transparent", "hover_color": self.colors["panel_alt"], "text_color": self.colors["text"], "anchor": "w"}

        new_branch_btn = ctk.CTkButton(sidebar, text="＋  Nova Branch", command=lambda: self._open_create_branch_dialog(dialog, on_created=lambda: [refresh_status_label(), reload_file_list()]), **btn_style)
        new_branch_btn.pack(fill="x", padx=8, pady=2)

        switch_branch_btn = ctk.CTkButton(sidebar, text="⇄  Trocar Branch", command=lambda: self._open_switch_branch_dialog(dialog, on_switched=lambda: [refresh_status_label(), reload_file_list()]), **btn_style)
        switch_branch_btn.pack(fill="x", padx=8, pady=2)

        history_btn = ctk.CTkButton(sidebar, text="☰  Histórico", command=lambda: self._open_commit_log_dialog(dialog), **btn_style)
        history_btn.pack(fill="x", padx=8, pady=(2, 12))

        ctk.CTkLabel(sidebar, text="Remoto", font=("Segoe UI", 11, "bold"), text_color=self.colors["text_dim"]).pack(anchor="w", padx=16, pady=(8, 4))

        def set_toolbar_busy(busy: bool, msg: str = ""):
            state = "disabled" if busy else "normal"
            for b in (new_branch_btn, switch_branch_btn, history_btn, pull_btn, push_btn, sync_btn):
                b.configure(state=state)
            if msg:
                feedback_label.configure(text=msg)

        def with_feedback(action_fn):
            def wrapped(*args, **kwargs):
                set_toolbar_busy(True, "Processando...")
                def on_done(ok, msg):
                    set_toolbar_busy(False, msg)
                    refresh_status_label()
                    reload_file_list()
                action_fn(on_done=on_done, *args, **kwargs)
            return wrapped

        pull_btn = ctk.CTkButton(sidebar, text="↓  Pull", command=lambda: with_feedback(self.git_pull)(), **btn_style)
        pull_btn.pack(fill="x", padx=8, pady=2)

        push_btn = ctk.CTkButton(sidebar, text="↑  Push", command=lambda: with_feedback(self.git_push)(), **btn_style)
        push_btn.pack(fill="x", padx=8, pady=2)

        sync_btn = ctk.CTkButton(sidebar, text="⟲  Sincronizar", fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"], text_color="#1e2127", font=("Segoe UI", 11, "bold"), height=30, anchor="center", command=lambda: with_feedback(self.git_sync)())
        sync_btn.pack(fill="x", padx=16, pady=(12, 2))

        feedback_label = ctk.CTkLabel(sidebar, text="", font=("Segoe UI", 10), text_color=self.colors["text_dim"], wraplength=160)
        feedback_label.pack(side="bottom", fill="x", padx=16, pady=16)

        header = ctk.CTkFrame(main_area, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        branch_label = ctk.CTkLabel(header, text=f"Branch: {branch or 'N/A'}", font=("Segoe UI", 14, "bold"), text_color=self.colors["accent"])
        branch_label.pack(side="left")

        def refresh_status_label():
            b, c = self.get_git_info()
            branch_label.configure(text=f"Branch: {b or 'N/A'}  |  {c} arquivos")

        refresh_btn = ctk.CTkButton(header, text="⟳  Refresh", width=70, height=26, font=("Segoe UI", 11), fg_color=self.colors["panel"], hover_color=self.colors["border"], text_color=self.colors["text"], command=lambda: [refresh_status_label(), reload_file_list()])
        refresh_btn.pack(side="right")

        list_header = ctk.CTkFrame(main_area, fg_color="transparent")
        list_header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(list_header, text="Arquivos Alterados", font=("Segoe UI", 12, "bold"), text_color=self.colors["text"]).pack(side="left")

        files_count_label = ctk.CTkLabel(list_header, text="", font=("Segoe UI", 10), text_color=self.colors["text_dim"])
        files_count_label.pack(side="left", padx=(8, 0))

        unstage_all_btn = ctk.CTkButton(list_header, text="Unstage Tudo", width=94, height=22, font=("Segoe UI", 10), fg_color="transparent", hover_color=self.colors["panel"], text_color=self.colors["text_dim"], command=lambda: unstage_all())
        unstage_all_btn.pack(side="right", padx=(4, 0))

        stage_all_btn = ctk.CTkButton(list_header, text="Stage Tudo", width=84, height=22, font=("Segoe UI", 10), fg_color="transparent", hover_color=self.colors["panel"], text_color=self.colors["add"], command=lambda: stage_all())
        stage_all_btn.pack(side="right")

        file_list_frame = ctk.CTkScrollableFrame(main_area, fg_color=self.colors["panel_alt"], corner_radius=4, border_width=1, border_color=self.colors["border"])
        file_list_frame.pack(fill="both", expand=True, pady=(0, 12))

        def toggle_stage(path, currently_staged):
            if currently_staged:
                self.unstage_file(path)
            else:
                self.stage_file(path)
            reload_file_list()
            refresh_status_label()

        def stage_all():
            subprocess.run(["git", "add", "."], cwd=self.ctx.project_root)
            self.async_update_status()
            reload_file_list()
            refresh_status_label()

        def unstage_all():
            subprocess.run(["git", "reset", "HEAD"], cwd=self.ctx.project_root)
            self.async_update_status()
            reload_file_list()
            refresh_status_label()

        def reload_file_list():
            for child in file_list_frame.winfo_children():
                child.destroy()

            status_data = self.get_status_data()

            if not status_data:
                files_count_label.configure(text="0 arquivos")
                ctk.CTkLabel(file_list_frame, text="Nenhuma alteração pendente.", font=("Segoe UI", 11), text_color=self.colors["text_dim"]).pack(pady=20)
                return

            files_count_label.configure(text=f"{len(status_data)} arquivo{'s' if len(status_data) != 1 else ''}")

            for code, path in status_data:
                char, color = "", self.colors["text"]
                if 'M' in code: char, color = "M", self.colors["mod"]
                elif 'A' in code or '?' in code: char, color = "A", self.colors["add"]
                elif 'D' in code: char, color = "D", self.colors["del"]
                elif 'R' in code: char, color = "R", self.colors["mod"]

                is_staged = code[0] not in (' ', '?')

                row = ctk.CTkFrame(file_list_frame, fg_color="transparent", corner_radius=4)
                row.pack(fill="x", padx=4, pady=1)

                def make_hover(r):
                    def on_enter(_e): r.configure(fg_color=self.colors["panel"])
                    def on_leave(_e): r.configure(fg_color="transparent")
                    return on_enter, on_leave

                on_enter, on_leave = make_hover(row)
                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)

                check_var = ctk.BooleanVar(value=is_staged)
                cb = ctk.CTkCheckBox(row, text="", variable=check_var, width=18, height=18, corner_radius=3,
                                      fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
                                      border_color=self.colors["border"],
                                      command=lambda p=path, s=is_staged: toggle_stage(p, s))
                cb.pack(side="left", padx=(6, 6), pady=4)
                cb.bind("<Enter>", on_enter)
                cb.bind("<Leave>", on_leave)

                badge = ctk.CTkLabel(row, text=char, width=18, font=("Consolas", 11, "bold"), text_color=color)
                badge.pack(side="left", padx=(0, 6))
                badge.bind("<Enter>", on_enter)
                badge.bind("<Leave>", on_leave)

                path_label = ctk.CTkLabel(row, text=path, font=("Consolas", 11), text_color=self.colors["text"], anchor="w")
                path_label.pack(side="left", fill="x", expand=True)
                path_label.bind("<Enter>", on_enter)
                path_label.bind("<Leave>", on_leave)

        reload_file_list()

        commit_frame = ctk.CTkFrame(main_area, fg_color="transparent")
        commit_frame.pack(fill="x")

        entry = ctk.CTkEntry(commit_frame, placeholder_text="Mensagem do commit...", fg_color=self.colors["panel_alt"], border_color=self.colors["border"], corner_radius=4, height=36)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry.focus_set()

        def execute_commit():
            msg = entry.get()
            if not msg: return

            status_data = self.get_status_data()
            staged = [p for c, p in status_data if c[0] not in (' ', '?')]
            if not staged:
                original_text = commit_btn.cget("text")
                commit_btn.configure(text="Nada staged!")
                dialog.after(1500, lambda: commit_btn.configure(text=original_text))
                return

            commit_btn.configure(state="disabled", text="Enviando...")

            def task():
                try:
                    subprocess.run(["git", "commit", "-m", msg], cwd=self.ctx.project_root, check=True)
                    self.ctx.window.after(0, lambda: [self.async_update_status(), dialog.destroy()])
                except subprocess.CalledProcessError:
                    self.ctx.window.after(0, lambda: commit_btn.configure(state="normal", text="✓  Commit"))

            threading.Thread(target=task, daemon=True).start()

        commit_btn = ctk.CTkButton(commit_frame, text="✓  Commit", width=110, height=36, font=("Segoe UI", 12, "bold"), fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"], text_color="#1e2127", command=execute_commit)
        commit_btn.pack(side="right")

        dialog.bind("<Return>", lambda e: execute_commit())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _open_create_branch_dialog(self, parent, on_created=None):
        popup = ctk.CTkToplevel(parent)
        popup.title("Nova Branch")
        popup.geometry("360x180")
        popup.attributes("-topmost", True)
        popup.configure(fg_color=self.colors["bg"])
        popup.focus_set()

        ctk.CTkLabel(popup, text="Nome da nova branch", font=("Segoe UI", 12, "bold"), text_color=self.colors["text"]).pack(pady=(20, 4), padx=20, anchor="w")
        entry = ctk.CTkEntry(popup, placeholder_text="feature/minha-branch", fg_color=self.colors["panel_alt"], border_color=self.colors["border"], corner_radius=4)
        entry.pack(fill="x", padx=20, pady=4)
        entry.focus_set()

        feedback = ctk.CTkLabel(popup, text="", font=("Segoe UI", 10), text_color=self.colors["danger"])
        feedback.pack(padx=20, anchor="w")

        def confirm():
            name = entry.get().strip()
            if not name:
                feedback.configure(text="Digite um nome válido.")
                return
            ok, msg = self.create_branch(name, checkout=True)
            if ok:
                popup.destroy()
                if on_created: on_created()
            else:
                feedback.configure(text=msg[:80])

        btn = ctk.CTkButton(popup, text="＋  Criar e Trocar", height=32, fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"], text_color="#1e2127", command=confirm)
        btn.pack(pady=16, padx=20, fill="x")

        popup.bind("<Return>", lambda e: confirm())
        popup.bind("<Escape>", lambda e: popup.destroy())

    def _open_commit_log_dialog(self, parent):
        ROW_H = 26
        GRAPH_PAD = 14
        MIN_TEXT_W = 380

        popup = ctk.CTkToplevel(parent)
        popup.title("Histórico de Commits")
        popup.geometry("680x640")
        popup.minsize(480, 420)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=self.colors["bg"])
        popup.focus_set()

        header = ctk.CTkFrame(popup, fg_color=self.colors["panel"], corner_radius=0)
        header.pack(fill="x")

        branch, _ = self.get_git_info()
        ctk.CTkLabel(header, text=f"Branch: {branch or 'N/A'}", font=("Segoe UI", 13, "bold"), text_color=self.colors["accent"]).pack(side="left", padx=16, pady=12)

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(header, textvariable=search_var, placeholder_text="Filtrar por mensagem, autor ou hash...", height=28, width=230, fg_color=self.colors["panel_alt"], border_color=self.colors["border"], corner_radius=4)
        search_entry.pack(side="left", padx=(12, 0), pady=12)

        refresh_btn = ctk.CTkButton(header, text="⟳  Refresh", width=70, height=26, font=("Segoe UI", 11), fg_color="transparent", hover_color=self.colors["panel_alt"], text_color=self.colors["text"], command=lambda: reload_log())
        refresh_btn.pack(side="right", padx=16, pady=12)

        canvas_frame = ctk.CTkFrame(popup, fg_color=self.colors["panel_alt"], corner_radius=0)
        canvas_frame.pack(fill="both", expand=True)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        graph_canvas = tk.Canvas(canvas_frame, bg=self.colors["panel_alt"], highlightthickness=0, cursor="hand2")
        graph_canvas.grid(row=0, column=0, sticky="nsew")

        vscroll = ctk.CTkScrollbar(canvas_frame, orientation="vertical", command=graph_canvas.yview)
        vscroll.grid(row=0, column=1, sticky="ns")
        graph_canvas.configure(yscrollcommand=vscroll.set)

        hscroll = ctk.CTkScrollbar(canvas_frame, orientation="horizontal", command=graph_canvas.xview)
        hscroll.grid(row=1, column=0, sticky="ew")
        graph_canvas.configure(xscrollcommand=hscroll.set)

        def _on_mousewheel(event): graph_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_shift_mousewheel(event): graph_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_wheel(_e):
            graph_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            graph_canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)
        def _unbind_wheel(_e):
            graph_canvas.unbind_all("<MouseWheel>")
            graph_canvas.unbind_all("<Shift-MouseWheel>")

        graph_canvas.bind("<Enter>", _bind_wheel)
        graph_canvas.bind("<Leave>", _unbind_wheel)

        detail_panel = ctk.CTkFrame(popup, fg_color=self.colors["panel"], corner_radius=0, height=76)
        detail_panel.pack(fill="x", side="bottom")
        detail_panel.pack_propagate(False)

        detail_label = ctk.CTkLabel(detail_panel, text="Clique em um commit para ver detalhes.", font=("Segoe UI", 11), text_color=self.colors["text_dim"], anchor="w", justify="left", wraplength=520)
        detail_label.pack(side="left", fill="both", expand=True, padx=16, pady=10)

        def copy_hash():
            sel = state.get("selected")
            if sel:
                popup.clipboard_clear()
                popup.clipboard_append(sel.get("full", sel["hash"]))
                copy_btn.configure(text="Copiado!")
                popup.after(1200, lambda: copy_btn.configure(text="Copiar Hash"))

        copy_btn = ctk.CTkButton(detail_panel, text="Copiar Hash", width=110, height=28, font=("Segoe UI", 10), fg_color=self.colors["panel_alt"], hover_color=self.colors["border"], text_color=self.colors["text"], command=copy_hash)
        copy_btn.pack(side="right", padx=16, pady=10)

        state = {"commits": None, "hover_idx": None, "selected": None, "selected_idx": None, "content_w": 420, "search_job": None, "resize_job": None, "tooltip": None}
        msg_font = tkfont.Font(family="Segoe UI", size=11)
        msg_font_bold = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        dim_font = tkfont.Font(family="Segoe UI", size=9)
        pill_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        hover_overlay = graph_canvas.create_rectangle(-10, -10, -10, -10, outline=self.colors["accent_hover"], width=1, fill="", state="hidden")
        selection_overlay = graph_canvas.create_rectangle(-10, -10, -10, -10, outline=self.colors["accent"], width=2, fill="", state="hidden")

        def lane_color(col: int) -> str: return self.graph_colors[col % len(self.graph_colors)]

        def set_hover(idx):
            if idx is None:
                graph_canvas.itemconfigure(hover_overlay, state="hidden")
                return
            cw = state["content_w"]
            y0, y1 = idx * ROW_H, (idx + 1) * ROW_H
            graph_canvas.coords(hover_overlay, 1, y0 + 1, cw - 1, y1 - 1)
            graph_canvas.itemconfigure(hover_overlay, state="normal")

        def set_selection(idx):
            if idx is None:
                graph_canvas.itemconfigure(selection_overlay, state="hidden")
                return
            cw = state["content_w"]
            y0, y1 = idx * ROW_H, (idx + 1) * ROW_H
            graph_canvas.coords(selection_overlay, 1, y0 + 1, cw - 1, y1 - 1)
            graph_canvas.itemconfigure(selection_overlay, state="normal")

        def _hide_tooltip():
            tw = state.get("tooltip")
            if tw is not None:
                try:
                    tw.destroy()
                except Exception:
                    pass
                state["tooltip"] = None

        def _position_tooltip(tw, x_root, y_root):
            tw.update_idletasks()
            tw_w = tw.winfo_width()
            tw_h = tw.winfo_height()
            screen_w = tw.winfo_screenwidth()
            screen_h = tw.winfo_screenheight()

            x = x_root + 16
            y = y_root + 16
            if x + tw_w > screen_w:
                x = x_root - tw_w - 16
            if y + tw_h > screen_h:
                y = y_root - tw_h - 16
            tw.geometry(f"+{int(x)}+{int(y)}")

        def _show_tooltip(idx, x_root, y_root):
            if not state["commits"] or idx is None or idx >= len(state["commits"]):
                _hide_tooltip()
                return
            c = state["commits"][idx]
            _hide_tooltip()

            tw = tk.Toplevel(popup)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg=self.colors["border"])

            inner = tk.Frame(tw, bg=self.colors["panel"], highlightthickness=0)
            inner.pack(padx=1, pady=1)

            tk.Label(
                inner, text=c["message"], bg=self.colors["panel"], fg="#ffffff",
                font=("Segoe UI", 10, "bold"), anchor="w", justify="left", wraplength=320
            ).pack(anchor="w", padx=10, pady=(8, 3))

            tk.Label(
                inner, text=f"Autor: {c['author']}", bg=self.colors["panel"], fg=self.colors["text_dim"],
                font=("Segoe UI", 9), anchor="w", justify="left"
            ).pack(anchor="w", padx=10)

            tk.Label(
                inner, text=f"Data: {c['date']}", bg=self.colors["panel"], fg=self.colors["text_dim"],
                font=("Segoe UI", 9), anchor="w", justify="left"
            ).pack(anchor="w", padx=10)

            tk.Label(
                inner, text=c["hash"], bg=self.colors["panel"], fg=self.colors["accent"],
                font=("Consolas", 9), anchor="w", justify="left"
            ).pack(anchor="w", padx=10, pady=(2, 8))

            _position_tooltip(tw, x_root, y_root)
            state["tooltip"] = tw

        def draw(commits, filter_text=""):
            graph_canvas.delete("commit_item")
            visible_w = max(graph_canvas.winfo_width(), 420)
            filter_text = (filter_text or "").strip().lower()

            if not commits:
                graph_canvas.create_text(20, 24, anchor="w", text="Nenhum commit.", fill=self.colors["text_dim"], font=("Segoe UI", 11), tags=("commit_item",))
                graph_canvas.configure(scrollregion=(0, 0, visible_w, 60))
                graph_canvas.itemconfigure(hover_overlay, state="hidden")
                graph_canvas.itemconfigure(selection_overlay, state="hidden")
                return

            max_col = max(max([c["col"]] + c["incoming"] + c["outgoing"] + c["passthrough"], default=0) for c in commits)
            col_w = 16 if max_col <= 6 else (12 if max_col <= 12 else 9)

            graph_w = GRAPH_PAD + max_col * col_w + 22
            tx = graph_w
            content_w = max(visible_w, graph_w + MIN_TEXT_W)
            total_h = len(commits) * ROW_H
            state["content_w"] = content_w

            def lane_x(col: int) -> float: return GRAPH_PAD + col * col_w

            for i, c in enumerate(commits):
                y0, y1 = i * ROW_H, (i + 1) * ROW_H
                yc = y0 + ROW_H / 2
                col_x = lane_x(c["col"])
                color = lane_color(c["col"])
                row_tag = f"row{i}"
                item_tags = ("commit_item", row_tag)

                matched = True
                if filter_text:
                    matched = filter_text in c["message"].lower() or filter_text in c["author"].lower() or filter_text in c["hash"].lower()

                if c["is_head"]:
                    row_bg = "#2c3a4d"
                elif i % 2 == 1:
                    row_bg = self.colors["panel"]
                else:
                    row_bg = self.colors["panel_alt"]

                graph_canvas.create_rectangle(0, y0, content_w, y1, fill=row_bg, width=0, tags=item_tags)

                for pcol in c["passthrough"]:
                    px = lane_x(pcol)
                    graph_canvas.create_line(px, y0, px, y1, fill=lane_color(pcol), width=2, tags=item_tags)

                if c["same_col_in"]: graph_canvas.create_line(col_x, y0, col_x, yc, fill=color, width=2, tags=item_tags)
                for icol in c["incoming"]:
                    ix = lane_x(icol)
                    graph_canvas.create_line(ix, y0, col_x, yc, fill=lane_color(icol), width=2, tags=item_tags)

                if c["same_col_out"]: graph_canvas.create_line(col_x, yc, col_x, y1, fill=color, width=2, tags=item_tags)
                for ocol in c["outgoing"]:
                    ox = lane_x(ocol)
                    graph_canvas.create_line(col_x, yc, ox, y1, fill=color, width=2, tags=item_tags)

                r = 5 if c["is_merge"] else (4 if col_w >= 12 else 3)
                graph_canvas.create_oval(col_x - r, yc - r, col_x + r, yc + r, fill=color, outline=self.colors["bg"], width=2, tags=item_tags)

                msg = c["message"]
                avail_px = content_w - tx - 70
                while msg and msg_font.measure(msg) > avail_px: msg = msg[:-1]
                if msg != c["message"]: msg = msg[:-1] + "…"

                if not matched:
                    msg_color = self.colors["text_dim"]
                else:
                    msg_color = "#ffffff" if c["is_head"] else self.colors["text"]
                row_font = msg_font_bold if c["is_head"] else msg_font

                graph_canvas.create_text(tx, yc, anchor="w", text=msg, fill=msg_color, font=row_font, tags=item_tags)
                msg_w = row_font.measure(msg)
                author_x = tx + msg_w + 12

                author_color = self.colors["text_dim"] if matched else self.colors["border"]
                graph_canvas.create_text(author_x, yc, anchor="w", text=c["author"], fill=author_color, font=dim_font, tags=item_tags)
                graph_canvas.create_text(content_w - 14, yc, anchor="e", text=c["hash"], fill=self.colors["text_dim"], font=("Consolas", 9), tags=item_tags)

                if c["is_head"] and branch:
                    label = branch if len(branch) <= 18 else branch[:16] + "…"
                    pill_w = pill_font.measure(label) + 16
                    pill_x = author_x + dim_font.measure(c["author"]) + 10
                    graph_canvas.create_rectangle(pill_x, yc - 9, pill_x + pill_w, yc + 9, fill=self.colors["accent"], outline="", width=0, tags=item_tags)
                    graph_canvas.create_text(pill_x + pill_w / 2, yc, text=label, fill="#1e2127", font=pill_font, tags=item_tags)

                graph_canvas.tag_bind(row_tag, "<Button-1>", lambda e, idx=i: on_select(idx))

            graph_canvas.configure(scrollregion=(0, 0, content_w, total_h))
            graph_canvas.tag_raise(hover_overlay)
            graph_canvas.tag_raise(selection_overlay)
            set_hover(state.get("hover_idx"))
            set_selection(state.get("selected_idx"))

        def on_select(idx):
            if not state["commits"] or idx >= len(state["commits"]): return
            c = state["commits"][idx]
            state["selected"] = c
            state["selected_idx"] = idx
            detail_label.configure(text=f"{c['hash']}  |  {c['author']}  |  {c['date']}\n{c['message']}")
            set_selection(idx)

        def on_motion(event):
            if not state["commits"]:
                return
            y = graph_canvas.canvasy(event.y)
            idx = int(y // ROW_H)
            if idx < 0 or idx >= len(state["commits"]): idx = None

            if idx != state.get("hover_idx"):
                state["hover_idx"] = idx
                set_hover(idx)
                if idx is None:
                    _hide_tooltip()
                else:
                    _show_tooltip(idx, event.x_root, event.y_root)
            elif idx is not None and state.get("tooltip") is not None:
                _position_tooltip(state["tooltip"], event.x_root, event.y_root)

        def on_canvas_leave(event):
            if state.get("hover_idx") is not None:
                state["hover_idx"] = None
                set_hover(None)
            _hide_tooltip()

        graph_canvas.bind("<Motion>", on_motion, add="+")
        graph_canvas.bind("<Leave>", on_canvas_leave, add="+")

        def reload_log():
            _hide_tooltip()
            state["commits"] = self.get_commit_graph()
            state["selected"] = None
            state["selected_idx"] = None
            state["hover_idx"] = None
            detail_label.configure(text="Clique em um commit para ver detalhes.")
            draw(state["commits"], search_var.get())

        def redraw_only(_event=None):
            if state.get("resize_job"): popup.after_cancel(state["resize_job"])
            state["resize_job"] = popup.after(80, lambda: draw(state["commits"], search_var.get()) if state["commits"] is not None else None)

        def on_search_change(*_a):
            if state.get("search_job"): popup.after_cancel(state["search_job"])
            state["search_job"] = popup.after(150, lambda: draw(state["commits"], search_var.get()) if state["commits"] is not None else None)

        search_var.trace_add("write", on_search_change)

        popup.after(30, reload_log)
        graph_canvas.bind("<Configure>", redraw_only)
        popup.bind("<Escape>", lambda e: popup.destroy())
        popup.protocol("WM_DELETE_WINDOW", lambda: [_hide_tooltip(), popup.destroy()])

    def _open_switch_branch_dialog(self, parent, on_switched=None):
        branches = self.get_branches()
        if not branches: return

        popup = ctk.CTkToplevel(parent)
        popup.title("Trocar Branch")
        popup.geometry("360x360")
        popup.minsize(320, 280)
        popup.attributes("-topmost", True)
        popup.configure(fg_color=self.colors["bg"])
        popup.focus_set()

        ctk.CTkLabel(popup, text="Selecione a branch", font=("Segoe UI", 12, "bold"), text_color=self.colors["text"]).pack(pady=(20, 4), padx=20, anchor="w")
        current_branch, _ = self.get_git_info()

        filter_entry = ctk.CTkEntry(popup, placeholder_text="Filtrar branches...", fg_color=self.colors["panel_alt"], border_color=self.colors["border"], corner_radius=4)
        filter_entry.pack(fill="x", padx=20, pady=4)
        filter_entry.focus_set()

        list_frame = ctk.CTkScrollableFrame(popup, fg_color=self.colors["panel_alt"], corner_radius=4, border_width=1, border_color=self.colors["border"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=8)

        feedback = ctk.CTkLabel(popup, text="", font=("Segoe UI", 10), text_color=self.colors["text_dim"])
        feedback.pack(padx=20, anchor="w")

        state = {"selected": current_branch if current_branch in branches else branches[0]}

        def confirm(target=None):
            name = target or state["selected"]
            if not name: return
            feedback.configure(text="Trocando...")
            popup.update_idletasks()
            self.switch_branch(name)
            popup.destroy()
            if on_switched: on_switched()

        def render_list(filter_text=""):
            for child in list_frame.winfo_children():
                child.destroy()

            filter_text = filter_text.strip().lower()
            shown = [b for b in branches if filter_text in b.lower()]

            if not shown:
                ctk.CTkLabel(list_frame, text="Nenhuma branch encontrada.", font=("Segoe UI", 11), text_color=self.colors["text_dim"]).pack(pady=12)
                return

            for b in shown:
                is_current = b == current_branch
                is_selected = b == state["selected"]
                row_color = self.colors["accent"] if is_selected else "transparent"
                row_text_color = "#1e2127" if is_selected else self.colors["text"]
                row_hover = self.colors["accent_hover"] if is_selected else self.colors["panel"]

                def select_and_render(name=b):
                    state["selected"] = name
                    render_list(filter_entry.get())

                btn = ctk.CTkButton(list_frame, text=(f"{b}  (atual)" if is_current else b), anchor="w", height=28,
                                     fg_color=row_color, hover_color=row_hover, text_color=row_text_color,
                                     font=("Segoe UI", 11), command=select_and_render)
                btn.pack(fill="x", padx=4, pady=2)
                btn.bind("<Double-Button-1>", lambda e, name=b: confirm(name))

        render_list()
        filter_entry.bind("<KeyRelease>", lambda e: render_list(filter_entry.get()))

        btn = ctk.CTkButton(popup, text="⇄  Trocar", height=32, fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"], text_color="#1e2127", command=lambda: confirm())
        btn.pack(pady=16, padx=20, fill="x")

        popup.bind("<Return>", lambda e: confirm())
        popup.bind("<Escape>", lambda e: popup.destroy())