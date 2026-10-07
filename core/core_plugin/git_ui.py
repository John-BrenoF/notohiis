import os
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox

import customtkinter as ctk

UI = "Segoe UI"
MONO = "Consolas"


class GitPanel:
    """Janela única com as quatro frentes de trabalho do Git."""

    TAB_CHANGES = "Alterações"
    TAB_HISTORY = "Histórico"
    TAB_BRANCHES = "Branches"
    TAB_REMOTE = "Remoto"
    TABS = (TAB_CHANGES, TAB_HISTORY, TAB_BRANCHES, TAB_REMOTE)

    ROW_H = 26
    GRAPH_PAD = 14
    MIN_TEXT_W = 380

    def __init__(self, plugin, master):
        self.plugin = plugin
        self.ctx = plugin.ctx
        self.colors = dict(plugin.colors)
        self.on_accent = self.colors.get("on_accent", "#14181f")
        c = self.colors

        self._changes = []
        self._selected_path = None
        self._pending_path = None
        self._rows = {}
        self._commits = []
        self._head_branch = ""
        self._commit_idx = None
        self._hover_idx = None
        self._branches = []
        self._branch_sel = None
        self._branch_rows = {}
        self._busy = False
        self._suppress_cmd = False
        self._job_search = None
        self._job_resize = None
        self._content_w = 640
        self._is_repo = False
        self._empty_shown = False
        self._has_remote = False

        win = self.win = ctk.CTkToplevel(master)
        win.title("Git — Notohiis")
        win.configure(fg_color=c["bg"])
        win.geometry("1020x660")
        win.minsize(840, 560)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        win.protocol("WM_DELETE_WINDOW", self.close)

        win.grid_rowconfigure(1, weight=1)
        win.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_empty_state()
        self._build_tabview()
        self._build_changes_tab()
        self._build_history_tab()
        self._build_branches_tab()
        self._build_remote_tab()
        self._build_footer()

        win.bind("<Escape>", lambda _e: self.close())
        win.bind("<F5>", lambda _e: self.refresh())
        win.bind("<Control-Return>", self._on_ctrl_return)
        for i, name in enumerate(self.TABS):
            win.bind(f"<Control-{i + 1}>", lambda _e, n=name: self.show_tab(n))

        self._center(master)
        self.tabview.set(self.TAB_CHANGES)
        self._sync_tab_colors()
        self.refresh()
        win.after(80, win.focus_set)

    def _alive(self) -> bool:
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def _after(self, fn):
        try:
            self.win.after(0, fn)
        except Exception:
            pass

    def _center(self, master):
        try:
            self.win.update_idletasks()
            if master is not None:
                self.win.transient(master)
            sw = self.win.winfo_screenwidth()
            sh = self.win.winfo_screenheight()
            w = self.win.winfo_width() or 1020
            h = self.win.winfo_height() or 660
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.win.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _pill(self, master, text, fg, text_color, font=(UI, 10, "bold")):
        """Rótulo em formato de pílula (dimensiona sozinho ao conteúdo)."""
        holder = ctk.CTkFrame(master, fg_color=fg, corner_radius=11)
        label = ctk.CTkLabel(
            holder, text=text, font=font, text_color=text_color, fg_color="transparent"
        )
        label.pack(padx=10, pady=3)
        return holder, label

    def _ghost_button(self, master, text, command, width=None, **kw):
        c = self.colors
        return ctk.CTkButton(
            master,
            text=text,
            width=width or 0,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color=c["panel_alt"],
            text_color=c["text"],
            font=(UI, 11),
            command=command,
            **kw,
        )

    def _build_header(self):
        c = self.colors
        head = ctk.CTkFrame(self.win, fg_color=c["panel"], corner_radius=0)
        head.grid(row=0, column=0, sticky="ew")

        self.close_btn = ctk.CTkButton(
            head, text="✕", width=34, height=28, corner_radius=6,
            fg_color="transparent", hover_color=c["panel_alt"],
            text_color=c["text_dim"], font=(UI, 12), command=self.close,
        )
        self.close_btn.pack(side="right", padx=(0, 14), pady=13)

        self.refresh_btn = self._ghost_button(head, "Atualizar", self.refresh, width=90)
        self.refresh_btn.pack(side="right", padx=(0, 6), pady=13)

        self.changes_pill, self.changes_lbl = self._pill(
            head, "…", c["panel_alt"], c["text_dim"]
        )
        self.changes_pill.pack(side="right", padx=(0, 12), pady=14)

        self.branch_pill, self.branch_lbl = self._pill(
            head, "  …", c["accent"], self.on_accent, font=(UI, 11, "bold")
        )
        self.branch_pill.pack(side="left", padx=(16, 12), pady=13)

        self.repo_lbl = ctk.CTkLabel(
            head, text="", font=(UI, 11), text_color=c["text_dim"],
            anchor="w", justify="left",
        )
        self.repo_lbl.pack(side="left", fill="x", expand=True, pady=14)

    def _build_empty_state(self):
        c = self.colors
        frame = ctk.CTkFrame(self.win, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=(10, 6))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            frame, fg_color=c["panel"], corner_radius=12,
            border_width=1, border_color=c["border"],
        )
        card.grid(row=0, column=0)

        self.empty_title = ctk.CTkLabel(
            card, text="", font=(UI, 15, "bold"), text_color=c["text"], anchor="w"
        )
        self.empty_title.pack(fill="x", padx=36, pady=(30, 6))

        self.empty_desc = ctk.CTkLabel(
            card, text="", font=(UI, 11), text_color=c["text_dim"],
            anchor="w", justify="left",
        )
        self.empty_desc.pack(fill="x", padx=36)

        ctk.CTkLabel(
            card, text="Ctrl+O abre uma pasta  ·  o editor funciona sem Git",
            font=(UI, 10), text_color=c["border"], anchor="w",
        ).pack(fill="x", padx=36, pady=(14, 30))

        self.empty_frame = frame

    def _build_tabview(self):
        c = self.colors
        self.tabview = ctk.CTkTabview(
            self.win,
            fg_color=c["bg"],
            border_width=0,
            segmented_button_fg_color=c["panel"],
            segmented_button_selected_color=c["accent"],
            segmented_button_selected_hover_color=c["accent_hover"],
            segmented_button_unselected_color=c["panel"],
            segmented_button_unselected_hover_color=c["panel_alt"],
            segmented_button_font=(UI, 12, "bold"),
            text_color=c["text"],
            text_color_disabled=c["border"],
            command=self._on_tab_change,
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=14, pady=(10, 6))

    def _build_changes_tab(self):
        c = self.colors
        tab = self.tabview.add(self.TAB_CHANGES)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1, minsize=270)
        tab.grid_columnconfigure(1, weight=2, minsize=340)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(bar, text="Alterações", font=(UI, 13, "bold"),
                     text_color=c["text"]).pack(side="left")
        self.changes_count = ctk.CTkLabel(bar, text="", font=(UI, 11),
                                          text_color=c["text_dim"])
        self.changes_count.pack(side="left", padx=(8, 0))

        self.unstage_all_btn = self._ghost_button(bar, "Unstage tudo", self._unstage_all)
        self.unstage_all_btn.pack(side="right", padx=(6, 0))
        self.stage_all_btn = self._ghost_button(bar, "Stage tudo", self._stage_all)
        self.stage_all_btn.pack(side="right")

        self.files_list = ctk.CTkScrollableFrame(
            tab, fg_color=c["panel_alt"], corner_radius=6,
            border_width=1, border_color=c["border"],
            scrollbar_button_color=c["border"], scrollbar_button_hover_color=c["accent"],
        )
        self.files_list.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        diff = ctk.CTkFrame(tab, fg_color="transparent")
        diff.grid(row=1, column=1, sticky="nsew")
        diff.grid_rowconfigure(1, weight=1)
        diff.grid_columnconfigure(0, weight=1)

        dhead = ctk.CTkFrame(diff, fg_color="transparent")
        dhead.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(dhead, text="Diff", font=(UI, 13, "bold"),
                     text_color=c["text"]).pack(side="left")
        self.diff_path_lbl = ctk.CTkLabel(dhead, text="", font=(MONO, 11),
                                          text_color=c["text_dim"], anchor="w")
        self.diff_path_lbl.pack(side="left", padx=(8, 0))
        self.diff_hint_lbl = ctk.CTkLabel(dhead, text="", font=(UI, 10),
                                          text_color=c["border"])
        self.diff_hint_lbl.pack(side="right")

        self.diff_box = ctk.CTkTextbox(
            diff, fg_color=c["panel_alt"], border_width=1, border_color=c["border"],
            corner_radius=6, font=(MONO, 11), wrap="word",
            scrollbar_button_color=c["border"], scrollbar_button_hover_color=c["accent"],
        )
        self.diff_box.grid(row=1, column=0, sticky="nsew")
        for tag, color in (("add", c["add"]), ("del", c["del"]),
                           ("hdr", c["accent"]), ("dim", c["text_dim"])):
            self.diff_box.tag_config(tag, foreground=color)

        cbar = ctk.CTkFrame(tab, fg_color="transparent")
        cbar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.commit_entry = ctk.CTkEntry(
            cbar, placeholder_text="Mensagem do commit  ·  Ctrl+Enter confirma",
            height=36, fg_color=c["panel_alt"], border_color=c["border"],
            corner_radius=6, font=(UI, 12),
        )
        self.commit_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.commit_entry.bind("<Return>", lambda _e: self._do_commit())

        self.commit_btn = ctk.CTkButton(
            cbar, text="✓  Commit", width=130, height=36, corner_radius=6,
            fg_color=c["accent"], hover_color=c["accent_hover"],
            text_color=self.on_accent, font=(UI, 12, "bold"),
            command=self._do_commit,
        )
        self.commit_btn.pack(side="right")

        self._clear_diff()

    def _build_history_tab(self):
        c = self.colors
        tab = self.tabview.add(self.TAB_HISTORY)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(bar, text="Histórico", font=(UI, 13, "bold"),
                     text_color=c["text"]).pack(side="left")
        self.hist_count = ctk.CTkLabel(bar, text="", font=(UI, 11),
                                       text_color=c["text_dim"])
        self.hist_count.pack(side="left", padx=(8, 0))

        self.hist_search = ctk.CTkEntry(
            bar, placeholder_text="Filtrar mensagem, autor ou hash…", width=260,
            height=28, fg_color=c["panel_alt"], border_color=c["border"],
            corner_radius=6, font=(UI, 11),
        )
        self.hist_search.pack(side="right", padx=(8, 0))
        self.hist_search.bind("<KeyRelease>", self._on_history_search)

        self.hist_reload_btn = self._ghost_button(
            bar, "Recarregar", self._reload_history, width=100
        )
        self.hist_reload_btn.pack(side="right")

        holder = ctk.CTkFrame(
            tab, fg_color=c["panel_alt"], corner_radius=6,
            border_width=1, border_color=c["border"],
        )
        holder.grid(row=1, column=0, sticky="nsew")
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_columnconfigure(0, weight=1)

        self.hist_canvas = tk.Canvas(
            holder, bg=c["panel_alt"], highlightthickness=0, cursor="hand2"
        )
        self.hist_canvas.grid(row=0, column=0, sticky="nsew")

        vsb = ctk.CTkScrollbar(holder, orientation="vertical",
                               command=self.hist_canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ctk.CTkScrollbar(holder, orientation="horizontal",
                               command=self.hist_canvas.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.hist_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._hover_rect = self.hist_canvas.create_rectangle(
            -10, -10, -10, -10, outline=c["accent_hover"], width=1, fill="", state="hidden"
        )
        self._sel_rect = self.hist_canvas.create_rectangle(
            -10, -10, -10, -10, outline=c["accent"], width=2, fill="", state="hidden"
        )

        self.f_msg = tkfont.Font(family=UI, size=11)
        self.f_msg_bold = tkfont.Font(family=UI, size=11, weight="bold")
        self.f_dim = tkfont.Font(family=UI, size=9)
        self.f_pill = tkfont.Font(family=UI, size=9, weight="bold")

        self.hist_canvas.bind("<Motion>", self._on_history_motion)
        self.hist_canvas.bind("<Leave>", self._on_history_leave)
        self.hist_canvas.bind("<Configure>", self._redraw_history)
        self.hist_canvas.bind("<Enter>", self._bind_wheel)
        self.hist_canvas.bind("<Leave>", self._unbind_wheel, add="+")

        detail = ctk.CTkFrame(
            tab, fg_color=c["panel"], corner_radius=6,
            border_width=1, border_color=c["border"],
        )
        detail.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.hist_detail = ctk.CTkLabel(
            detail, text="Selecione um commit para ver os detalhes.",
            font=(UI, 11), text_color=c["text_dim"], anchor="w", justify="left",
        )
        self.hist_detail.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.hist_copy_btn = ctk.CTkButton(
            detail, text="Copiar hash", width=100, height=28, corner_radius=6,
            fg_color=c["panel_alt"], hover_color=c["border"],
            text_color=c["text"], font=(UI, 10), command=self._copy_hash,
        )
        self.hist_copy_btn.pack(side="right", padx=12, pady=8)

    def _build_branches_tab(self):
        c = self.colors
        tab = self.tabview.add(self.TAB_BRANCHES)
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(bar, text="Branches", font=(UI, 13, "bold"),
                     text_color=c["text"]).pack(side="left")
        self.branch_count = ctk.CTkLabel(bar, text="", font=(UI, 11),
                                         text_color=c["text_dim"])
        self.branch_count.pack(side="left", padx=(8, 0))

        self.branch_filter = ctk.CTkEntry(
            bar, placeholder_text="Filtrar branches…", width=220, height=28,
            fg_color=c["panel_alt"], border_color=c["border"],
            corner_radius=6, font=(UI, 11),
        )
        self.branch_filter.pack(side="right")
        self.branch_filter.bind("<KeyRelease>", lambda _e: self._reload_branches())

        self.branch_list = ctk.CTkScrollableFrame(
            tab, fg_color=c["panel_alt"], corner_radius=6,
            border_width=1, border_color=c["border"],
            scrollbar_button_color=c["border"], scrollbar_button_hover_color=c["accent"],
        )
        self.branch_list.grid(row=1, column=0, sticky="nsew")

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        right = ctk.CTkFrame(actions, fg_color="transparent")
        right.pack(side="right")
        self.branch_delete_btn = ctk.CTkButton(
            right, text="Excluir", width=90, height=32, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=c["danger"],
            hover_color=c["panel_alt"], text_color=c["danger"], font=(UI, 11),
            command=self._delete_branch,
        )
        self.branch_delete_btn.pack(side="right", padx=(6, 0))
        self.branch_switch_btn = ctk.CTkButton(
            right, text="Trocar branch", width=140, height=32, corner_radius=6,
            fg_color=c["accent"], hover_color=c["accent_hover"],
            text_color=self.on_accent, font=(UI, 11, "bold"),
            command=self._switch_branch,
        )
        self.branch_switch_btn.pack(side="right")

        left = ctk.CTkFrame(actions, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.new_branch_entry = ctk.CTkEntry(
            left, placeholder_text="nome-da-branch", height=32,
            fg_color=c["panel_alt"], border_color=c["border"],
            corner_radius=6, font=(UI, 11),
        )
        self.new_branch_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.new_branch_entry.bind("<Return>", lambda _e: self._create_branch())
        self.branch_create_btn = ctk.CTkButton(
            left, text="+ Criar branch", width=140, height=32, corner_radius=6,
            fg_color=c["panel"], hover_color=c["panel_alt"], border_width=1,
            border_color=c["border"], text_color=c["text"], font=(UI, 11),
            command=self._create_branch,
        )
        self.branch_create_btn.pack(side="left")

    def _build_remote_tab(self):
        c = self.colors
        tab = self.tabview.add(self.TAB_REMOTE)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(
            tab, fg_color=c["panel"], corner_radius=8,
            border_width=1, border_color=c["border"],
        )
        info.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.remote_state_pill, self.remote_state_lbl = self._pill(
            info, "—", c["panel_alt"], c["text_dim"]
        )
        self.remote_state_pill.pack(side="right", padx=12, pady=12)

        box = ctk.CTkFrame(info, fg_color="transparent")
        box.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.remote_title_lbl = ctk.CTkLabel(
            box, text="Nenhum remoto configurado", font=(UI, 12, "bold"),
            text_color=c["text"], anchor="w",
        )
        self.remote_title_lbl.pack(fill="x")
        self.remote_url_lbl = ctk.CTkLabel(
            box, text="", font=(MONO, 10), text_color=c["text_dim"], anchor="w"
        )
        self.remote_url_lbl.pack(fill="x")

        cards = ctk.CTkFrame(tab, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1, uniform="remote")

        specs = (
            ("pull", "↓  Pull", "Baixa as alterações do remoto e mescla na branch atual."),
            ("push", "↑  Push", "Envia os commits locais para o remoto."),
            ("sync", "Sincronizar", "Faz pull e em seguida push — mantém tudo alinhado."),
        )
        self.remote_btns = {}
        for i, (kind, title, desc) in enumerate(specs):
            card = ctk.CTkFrame(
                cards, fg_color=c["panel"], corner_radius=8,
                border_width=1, border_color=c["border"],
            )
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0, 8) if i < 2 else 0)
            ctk.CTkLabel(card, text=title, font=(UI, 13, "bold"),
                         text_color=c["text"], anchor="w").pack(
                fill="x", padx=14, pady=(14, 4))
            ctk.CTkLabel(card, text=desc, font=(UI, 10), text_color=c["text_dim"],
                         anchor="w", justify="left", wraplength=210).pack(
                fill="x", padx=14, pady=(0, 12))
            btn = ctk.CTkButton(
                card, text="Executar", height=32, corner_radius=6,
                fg_color=c["panel_alt"], hover_color=c["border"],
                text_color=c["text"], font=(UI, 11, "bold"),
                state="disabled",
                command=lambda k=kind: self._remote_action(k),
            )
            btn.pack(fill="x", padx=14, pady=(0, 14))
            self.remote_btns[kind] = btn

        log_frame = ctk.CTkFrame(
            tab, fg_color=c["panel"], corner_radius=8,
            border_width=1, border_color=c["border"],
        )
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        lhead = ctk.CTkFrame(log_frame, fg_color="transparent")
        lhead.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        ctk.CTkLabel(lhead, text="Atividade", font=(UI, 11, "bold"),
                     text_color=c["text_dim"]).pack(side="left")
        self._ghost_button(lhead, "Limpar", self._clear_log, width=80).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            log_frame, fg_color=c["panel_alt"], border_width=0,
            font=(MONO, 10), activate_scrollbars=True,
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        for tag, color in (("ok", c["add"]), ("err", c["del"]), ("dim", c["text_dim"])):
            self.log_box.tag_config(tag, foreground=color)
        self._log("Painel Git aberto.", "dim")

    def _build_footer(self):
        c = self.colors
        foot = ctk.CTkFrame(self.win, fg_color=c["panel"], corner_radius=0)
        foot.grid(row=2, column=0, sticky="ew")

        self.footer_status = ctk.CTkLabel(
            foot, text="Pronto.", font=(UI, 10), text_color=c["text_dim"], anchor="w"
        )
        self.footer_status.pack(side="left", padx=16, pady=7)

        ctk.CTkLabel(
            foot, text="Ctrl+1..4 abas  ·  F5 atualizar  ·  Esc fecha",
            font=(UI, 10), text_color=c["border"], anchor="e",
        ).pack(side="right", padx=16, pady=7)

    def show_tab(self, name):
        if not self._alive() or name not in self.TABS:
            return
        if not self._is_repo:
            return
        try:
            if self.tabview.get() == name:
                self._refresh_tab(name)
                return
            self._suppress_cmd = True
            self.tabview.set(name)
            self._suppress_cmd = False
            self._sync_tab_colors()
            self._refresh_tab(name)
        except Exception:
            self._suppress_cmd = False

    def _on_tab_change(self):
        if self._suppress_cmd:
            return
        self._sync_tab_colors()
        self._refresh_tab(self.tabview.get())

    def _sync_tab_colors(self):
        try:
            buttons = self.tabview._segmented_button._buttons_dict
            current = self.tabview.get()
        except Exception:
            return
        for value, btn in buttons.items():
            try:
                btn.configure(
                    text_color=self.on_accent if value == current
                    else self.colors["text"]
                )
            except Exception:
                pass

    def _refresh_tab(self, name):
        if not self._alive():
            return
        if name == self.TAB_CHANGES:
            self._reload_changes()
        elif name == self.TAB_HISTORY:
            self._reload_history()
        elif name == self.TAB_BRANCHES:
            self._reload_branches()
        elif name == self.TAB_REMOTE:
            self._reload_remote()
    def refresh(self):
        if not self._alive():
            return
        self._refresh_header()
        if self._is_repo:
            self._refresh_tab(self.tabview.get())

    def _refresh_header(self):
        c = self.colors
        root = self.ctx.project_root
        is_repo = bool(root) and self.plugin.is_repo()
        self._is_repo = is_repo

        if is_repo:
            branch, changes = self.plugin.get_git_info()
            self.branch_lbl.configure(text=f"  {branch or 'sem branch'}")
            if changes:
                self.changes_pill.configure(fg_color=c["panel_alt"])
                self.changes_lbl.configure(
                    text=f"{changes} alteração{'ões' if changes != 1 else ''}",
                    text_color=c["mod"],
                )
            else:
                self.changes_pill.configure(fg_color=c["panel_alt"])
                self.changes_lbl.configure(text="limpo", text_color=c["add"])
        else:
            self.branch_lbl.configure(text="  — ")
            self.changes_pill.configure(fg_color=c["panel_alt"])
            self.changes_lbl.configure(text="sem repositório", text_color=c["text_dim"])

        self.repo_lbl.configure(text=root or "Nenhuma pasta aberta")
        self._update_repo_state(root, is_repo)

    def _update_repo_state(self, root, is_repo):
        ready = bool(root) and is_repo
        if ready:
            if self._empty_shown:
                self.empty_frame.grid_remove()
                self.tabview.grid(row=1, column=0, sticky="nsew",
                                  padx=14, pady=(10, 6))
                self._empty_shown = False
            try:
                self.tabview._segmented_button.configure(state="normal")
            except Exception:
                pass
            return

        if not root:
            self.empty_title.configure(text="Nenhuma pasta aberta")
            self.empty_desc.configure(
                text="Abra uma pasta de projeto para ver o estado do Git.\n"
                     "Enquanto isso, o editor está plenamente utilizável."
            )
        else:
            self.empty_title.configure(text="Esta pasta não é um repositório Git")
            self.empty_desc.configure(
                text="Execute `git init` ou clone um repositório para usar o painel.\n"
                     "Enquanto isso, o editor está plenamente utilizável."
            )
        try:
            self.tabview._segmented_button.configure(state="disabled")
        except Exception:
            pass
        if not self._empty_shown:
            self.tabview.grid_remove()
            self.empty_frame.grid(row=1, column=0, sticky="nsew",
                                  padx=14, pady=(10, 6))
            self._empty_shown = True

    def _set_footer(self, text, error=False):
        if not self._alive():
            return
        color = self.colors["danger"] if error else self.colors["text_dim"]
        self.footer_status.configure(text=text, text_color=color)

    def _set_busy(self, busy, msg=""):
        self._busy = busy
        state = "disabled" if busy else "normal"
        widgets = (
            self.refresh_btn, self.commit_btn, self.commit_entry,
            self.stage_all_btn, self.unstage_all_btn,
            self.branch_create_btn, self.branch_switch_btn,
            self.branch_delete_btn, self.new_branch_entry,
        )
        for w in widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass
        remote_state = "normal" if (not busy and self._has_remote) else "disabled"
        for w in self.remote_btns.values():
            try:
                w.configure(state=remote_state)
            except Exception:
                pass
        if msg:
            self._set_footer(msg)

    def _run_bg(self, work, on_done=None, busy=False, busy_msg=""):
        """Executa `work` numa thread e devolve o resultado para a UI."""
        if not self._alive():
            return
        if busy:
            self._set_busy(True, busy_msg or "Processando…")

        def task():
            try:
                result = work()
            except Exception as e: 
                result = (False, str(e) or e.__class__.__name__)

            def deliver():
                if not self._alive():
                    return
                if busy:
                    self._set_busy(False)
                if on_done is not None:
                    on_done(result)

            self._after(deliver)

        threading.Thread(target=task, daemon=True).start()

    @staticmethod
    def _is_result(res):
        return isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], bool)

    def _reload_changes(self):
        if not self._alive():
            return
        c = self.colors
        self._changes = self.plugin.get_status_data()
        total = len(self._changes)
        staged = [p for code, p in self._changes if code[:1] not in (" ", "?")]

        if total:
            self.changes_count.configure(
                text=f"{total} arquivo{'s' if total != 1 else ''} · "
                     f"{len(staged)} staged"
            )
        else:
            self.changes_count.configure(text="")
        self.stage_all_btn.configure(state="normal" if total else "disabled")
        self.unstage_all_btn.configure(state="normal" if staged else "disabled")

        for child in self.files_list.winfo_children():
            child.destroy()
        self._rows = {}

        if not total:
            ctk.CTkLabel(
                self.files_list, text="✓  Nenhuma alteração pendente.",
                font=(UI, 12), text_color=c["add"],
            ).pack(pady=26)
        else:
            for code, path in self._changes:
                self._rows[path] = self._make_row(code, path)

        target = self._pending_path or self._selected_path
        self._pending_path = None
        if target:
            self._selected_path = target
            self._apply_selection()
            self._load_diff(target)
        else:
            self._selected_path = None
            self._clear_diff()

    def _status_char(self, code):
        c = self.colors
        if "M" in code:
            return "M", c["mod"]
        if "A" in code or "?" in code:
            return "A", c["add"]
        if "D" in code:
            return "D", c["del"]
        if "R" in code:
            return "R", c["mod"]
        return "·", c["text_dim"]

    def _make_row(self, code, path):
        c = self.colors
        staged = code[:1] not in (" ", "?")
        char, color = self._status_char(code)

        row = ctk.CTkFrame(self.files_list, fg_color="transparent", corner_radius=4)
        row.pack(fill="x", padx=5, pady=1)

        def on_enter(_e, r=row, p=path):
            if p != self._selected_path:
                r.configure(fg_color=c["panel"])

        def on_leave(_e, r=row, p=path):
            if p != self._selected_path:
                r.configure(fg_color="transparent")

        for seq in ("<Enter>", "<Leave>"):
            row.bind(seq, on_enter if seq == "<Enter>" else on_leave)

        cb = ctk.CTkCheckBox(
            row, text="", width=18, height=18, checkbox_width=18, checkbox_height=18,
            corner_radius=3, fg_color=c["accent"], hover_color=c["accent_hover"],
            border_color=c["border"], variable=ctk.BooleanVar(value=staged),
            command=lambda p=path, s=staged: self._on_toggle(p, s),
        )
        cb.pack(side="left", padx=(8, 6), pady=5)

        badge = ctk.CTkLabel(row, text=char, width=16, font=(MONO, 11, "bold"),
                             text_color=color)
        badge.pack(side="left", padx=(0, 6))
        badge.bind("<Button-1>", lambda _e, p=path: self._select_file(p))

        lbl = ctk.CTkLabel(row, text=path, font=(MONO, 11), text_color=c["text"],
                           anchor="w", height=22)
        lbl.pack(side="left", fill="x", expand=True, pady=4)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)
        lbl.bind("<Button-1>", lambda _e, p=path: self._select_file(p))

        return {"frame": row, "label": lbl}

    def _select_file(self, path):
        if self._selected_path == path:
            return
        self._selected_path = path
        self._apply_selection()
        self._load_diff(path)

    def _apply_selection(self):
        c = self.colors
        for path, parts in self._rows.items():
            selected = path == self._selected_path
            parts["frame"].configure(fg_color=c["panel"] if selected else "transparent")
            parts["label"].configure(text_color=c["accent"] if selected else c["text"])

    def _on_toggle(self, path, staged):
        def work():
            if staged:
                self.plugin.unstage_file(path)
            else:
                self.plugin.stage_file(path)

        self._run_bg(work, lambda _r: self.refresh())

    def _stage_all(self):
        self._run_bg(lambda: self.plugin.stage_all(), lambda _r: self.refresh())

    def _unstage_all(self):
        self._run_bg(lambda: self.plugin.unstage_all(), lambda _r: self.refresh())

    def _on_ctrl_return(self, _event=None):
        self._do_commit()

    def _do_commit(self):
        if self._busy:
            return
        msg = self.commit_entry.get().strip()
        if not msg:
            self._set_footer("Escreva uma mensagem para o commit.", error=True)
            self.commit_entry.focus_set()
            return

        staged = [p for code, p in self._changes if code[:1] not in (" ", "?")]
        if not staged:
            self._set_footer(
                "Nada staged: marque os arquivos antes de commitar.", error=True
            )
            return

        def done(res):
            if not self._is_result(res):
                return
            ok, text = res
            if ok:
                self.commit_entry.delete(0, "end")
                self._set_footer(text)
                self.refresh()
            else:
                self._set_footer(text, error=True)

        self._run_bg(lambda: self.plugin.commit(msg), done,
                     busy=True, busy_msg="Commitando…")

    def _is_staged(self, path):
        for code, p in self._changes:
            if p == path:
                return code[:1] not in (" ", "?")
        return False

    def _clear_diff(self):
        self.diff_path_lbl.configure(text="")
        self.diff_hint_lbl.configure(text="")
        self.diff_box.configure(state="normal")
        self.diff_box.delete("1.0", "end")
        self.diff_box.insert(
            "end",
            "Selecione um arquivo na lista para visualizar as diferenças.",
            "dim",
        )
        self.diff_box.configure(state="disabled")

    def _load_diff(self, path):
        if path is None:
            self._clear_diff()
            return
        staged = self._is_staged(path)
        self.diff_path_lbl.configure(text=os.path.basename(path))
        self.diff_hint_lbl.configure(
            text="index (staged)" if staged else "working tree"
        )
        self.diff_box.configure(state="normal")
        self.diff_box.delete("1.0", "end")
        self.diff_box.insert("end", "Calculando diff…", "dim")
        self.diff_box.configure(state="disabled")

        self._run_bg(
            lambda: self.plugin.get_file_diff(path, staged=staged),
            lambda text: self._fill_diff(path, text),
        )

    def _fill_diff(self, path, text):
        if not self._alive() or self._selected_path != path:
            return
        box = self.diff_box
        box.configure(state="normal")
        box.delete("1.0", "end")

        text = (text or "").strip()
        if not text:
            box.insert(
                "end",
                "Sem diferenças para exibir.\n\n"
                "Arquivos não rastreados só aparecem aqui após o primeiro `git add`.",
                "dim",
            )
        else:
            for line in text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    box.insert("end", line + "\n", "add")
                elif line.startswith("-") and not line.startswith("---"):
                    box.insert("end", line + "\n", "del")
                elif (line.startswith("@@") or line.startswith("diff ")
                      or line.startswith("index ") or line.startswith("---")
                      or line.startswith("+++")):
                    box.insert("end", line + "\n", "hdr")
                else:
                    box.insert("end", line + "\n")
        box.configure(state="disabled")
        box._textbox.see("1.0")

    def _reload_history(self):
        if not self._alive():
            return
        self._draw_history_message("Carregando histórico…")

        def work():
            commits = self.plugin.get_commit_graph()
            branch, _ = self.plugin.get_git_info()
            return commits, branch

        def done(res):
            if not self._alive():
                return
            if self._is_result(res):
                self._draw_history_message(f"Falha ao ler o histórico: {res[1]}")
                return
            commits, branch = res
            self._commits = commits
            self._head_branch = branch
            self._commit_idx = None
            self._hover_idx = None
            self.hist_count.configure(
                text=f"{len(commits)} commit{'s' if len(commits) != 1 else ''}"
            )
            self.hist_detail.configure(
                text="Selecione um commit para ver os detalhes."
            )
            self._draw_history(self.hist_search.get())

        self._run_bg(work, done)

    def _draw_history_message(self, message):
        canvas = self.hist_canvas
        canvas.delete("commit_item")
        canvas.itemconfigure(self._hover_rect, state="hidden")
        canvas.itemconfigure(self._sel_rect, state="hidden")
        canvas.create_text(
            24, 28, anchor="nw", text=message, fill=self.colors["text_dim"],
            font=(UI, 11), tags=("commit_item",),
        )
        canvas.configure(scrollregion=(0, 0, max(canvas.winfo_width(), 420), 80))

    def _lane_color(self, col):
        palette = self.plugin.graph_colors or ["#61afef"]
        return palette[col % len(palette)]

    def _set_hover(self, idx):
        if idx is None:
            self.hist_canvas.itemconfigure(self._hover_rect, state="hidden")
            return
        y0, y1 = idx * self.ROW_H, (idx + 1) * self.ROW_H
        self.hist_canvas.coords(self._hover_rect, 1, y0 + 1, self._content_w - 1, y1 - 1)
        self.hist_canvas.itemconfigure(self._hover_rect, state="normal")

    def _set_selection(self, idx):
        if idx is None:
            self.hist_canvas.itemconfigure(self._sel_rect, state="hidden")
            return
        y0, y1 = idx * self.ROW_H, (idx + 1) * self.ROW_H
        self.hist_canvas.coords(self._sel_rect, 1, y0 + 1, self._content_w - 1, y1 - 1)
        self.hist_canvas.itemconfigure(self._sel_rect, state="normal")

    def _draw_history(self, filter_text=""):
        c = self.colors
        canvas = self.hist_canvas
        canvas.delete("commit_item")
        commits = self._commits
        visible_w = max(canvas.winfo_width(), 420)
        filter_text = (filter_text or "").strip().lower()

        if not commits:
            self._draw_history_message("Nenhum commit encontrado.")
            return

        max_col = max(
            max([cmt["col"]] + cmt["incoming"] + cmt["outgoing"] + cmt["passthrough"],
                default=0)
            for cmt in commits
        )
        col_w = 16 if max_col <= 6 else (12 if max_col <= 12 else 9)
        graph_w = self.GRAPH_PAD + max_col * col_w + 22
        tx = graph_w
        content_w = max(visible_w, graph_w + self.MIN_TEXT_W)
        total_h = len(commits) * self.ROW_H
        self._content_w = content_w

        def lane_x(col):
            return self.GRAPH_PAD + col * col_w

        for i, cmt in enumerate(commits):
            y0, y1 = i * self.ROW_H, (i + 1) * self.ROW_H
            yc = y0 + self.ROW_H / 2
            col_x = lane_x(cmt["col"])
            color = self._lane_color(cmt["col"])
            row_tag = f"row{i}"
            tags = ("commit_item", row_tag)

            matched = (
                not filter_text
                or filter_text in cmt["message"].lower()
                or filter_text in cmt["author"].lower()
                or filter_text in cmt["hash"].lower()
            )

            if cmt["is_head"]:
                row_bg = c["panel"]
            elif i % 2 == 1:
                row_bg = c["panel_alt"]
            else:
                row_bg = c["bg"]

            canvas.create_rectangle(0, y0, content_w, y1, fill=row_bg, width=0, tags=tags)

            for pcol in cmt["passthrough"]:
                px = lane_x(pcol)
                canvas.create_line(px, y0, px, y1, fill=self._lane_color(pcol),
                                   width=2, tags=tags)

            if cmt["same_col_in"]:
                canvas.create_line(col_x, y0, col_x, yc, fill=color, width=2, tags=tags)
            for icol in cmt["incoming"]:
                ix = lane_x(icol)
                canvas.create_line(ix, y0, col_x, yc, fill=self._lane_color(icol),
                                   width=2, tags=tags)

            if cmt["same_col_out"]:
                canvas.create_line(col_x, yc, col_x, y1, fill=color, width=2, tags=tags)
            for ocol in cmt["outgoing"]:
                ox = lane_x(ocol)
                canvas.create_line(col_x, yc, ox, y1, fill=color, width=2, tags=tags)

            r = 5 if cmt["is_merge"] else (4 if col_w >= 12 else 3)
            canvas.create_oval(col_x - r, yc - r, col_x + r, yc + r, fill=color,
                               outline=c["bg"], width=2, tags=tags)

            row_font = self.f_msg_bold if cmt["is_head"] else self.f_msg
            msg_color = c["text"] if matched else c["border"]

            author = cmt["author"]
            author_w = self.f_dim.measure(author)

            pill_label = ""
            pill_w = 0
            if cmt["is_head"] and self._head_branch:
                pill_label = self._head_branch
                if len(pill_label) > 18:
                    pill_label = pill_label[:16] + "…"
                pill_w = self.f_pill.measure(pill_label) + 16

            reserved = author_w + 24 + 70 + (pill_w + 12 if pill_w else 0)
            avail_px = max(content_w - tx - reserved, 60)

            msg = cmt["message"]
            while msg and row_font.measure(msg) > avail_px:
                msg = msg[:-1]
            if msg != cmt["message"]:
                msg = (msg[:-1] + "…") if msg else "…"

            canvas.create_text(tx, yc, anchor="w", text=msg, fill=msg_color,
                               font=row_font, tags=tags)
            author_x = tx + row_font.measure(msg) + 12

            canvas.create_text(author_x, yc, anchor="w", text=author,
                               fill=c["text_dim"], font=self.f_dim, tags=tags)
            canvas.create_text(content_w - 14, yc, anchor="e", text=cmt["hash"],
                               fill=c["text_dim"], font=(MONO, 9), tags=tags)

            if pill_label:
                pill_x = author_x + author_w + 10
                canvas.create_rectangle(pill_x, yc - 9, pill_x + pill_w, yc + 9,
                                        fill=c["accent"], outline="", width=0, tags=tags)
                canvas.create_text(pill_x + pill_w / 2, yc, text=pill_label,
                                   fill=self.on_accent, font=self.f_pill, tags=tags)

            canvas.tag_bind(row_tag, "<Button-1>", lambda _e, idx=i: self._on_history_select(idx))

        canvas.configure(scrollregion=(0, 0, content_w, total_h))
        canvas.tag_raise(self._hover_rect)
        canvas.tag_raise(self._sel_rect)
        self._set_hover(self._hover_idx)
        self._set_selection(self._commit_idx)

    def _on_history_select(self, idx):
        if not self._commits or idx >= len(self._commits):
            return
        cmt = self._commits[idx]
        self._commit_idx = idx
        self.hist_detail.configure(
            text=f"{cmt['hash']}  ·  {cmt['author']}  ·  {cmt['date']}\n{cmt['message']}"
        )
        self._set_selection(idx)

    def _on_history_motion(self, event):
        if not self._commits:
            return
        y = self.hist_canvas.canvasy(event.y)
        idx = int(y // self.ROW_H)
        if idx < 0 or idx >= len(self._commits):
            idx = None
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._set_hover(idx)

    def _on_history_leave(self, _event):
        if self._hover_idx is not None:
            self._hover_idx = None
            self._set_hover(None)

    def _on_history_search(self, _event):
        if self._job_search:
            self.win.after_cancel(self._job_search)
        self._job_search = self.win.after(
            150, lambda: self._draw_history(self.hist_search.get())
        )

    def _redraw_history(self, _event=None):
        if self._job_resize:
            self.win.after_cancel(self._job_resize)
        self._job_resize = self.win.after(
            80,
            lambda: self._draw_history(self.hist_search.get())
            if self._commits else None,
        )

    def _bind_wheel(self, _event):
        self.hist_canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.hist_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_wheel)

    def _unbind_wheel(self, _event):
        self.hist_canvas.unbind_all("<MouseWheel>")
        self.hist_canvas.unbind_all("<Shift-MouseWheel>")

    def _on_wheel(self, event):
        self.hist_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_wheel(self, event):
        self.hist_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _copy_hash(self):
        if self._commit_idx is None or self._commit_idx >= len(self._commits):
            self._set_footer("Selecione um commit primeiro.", error=True)
            return
        cmt = self._commits[self._commit_idx]
        self.win.clipboard_clear()
        self.win.clipboard_append(cmt.get("full") or cmt["hash"])
        self._set_footer("Hash copiado para a área de transferência.")

    def _reload_branches(self):
        if not self._alive():
            return
        c = self.colors
        self._branches = self.plugin.get_branch_details()
        flt = self.branch_filter.get().strip().lower()
        shown = [b for b in self._branches if flt in b["name"].lower()]

        self.branch_count.configure(
            text=f"{len(self._branches)} local{'eis' if len(self._branches) != 1 else ''}"
        )

        for child in self.branch_list.winfo_children():
            child.destroy()
        self._branch_rows = {}

        if not self._branches:
            ctk.CTkLabel(self.branch_list, text="Nenhuma branch encontrada.",
                         font=(UI, 11), text_color=c["text_dim"]).pack(pady=20)
        elif not shown:
            ctk.CTkLabel(self.branch_list, text="Nenhuma branch corresponde ao filtro.",
                         font=(UI, 11), text_color=c["text_dim"]).pack(pady=20)
        else:
            for b in shown:
                self._branch_rows[b["name"]] = self._make_branch_row(b)

        if self._branch_sel not in self._branch_rows:
            current = next((b["name"] for b in self._branches if b["current"]), None)
            self._branch_sel = current if current in self._branch_rows else (
                next(iter(self._branch_rows), None)
            )
        self._apply_branch_selection()

        current = next((b["name"] for b in self._branches if b["current"]), None)
        has_selection = bool(self._branch_sel)
        self.branch_switch_btn.configure(
            state="normal" if has_selection and self._branch_sel != current else "disabled"
        )
        self.branch_delete_btn.configure(
            state="normal" if has_selection and self._branch_sel != current else "disabled"
        )

    def _make_branch_row(self, b):
        c = self.colors
        row = ctk.CTkFrame(self.branch_list, fg_color="transparent", corner_radius=4)
        row.pack(fill="x", padx=5, pady=1)

        def on_enter(_e, r=row, n=b["name"]):
            if n != self._branch_sel:
                r.configure(fg_color=c["panel"])

        def on_leave(_e, r=row, n=b["name"]):
            if n != self._branch_sel:
                r.configure(fg_color="transparent")

        pill = None
        if b["current"]:
            pill, _ = self._pill(row, "atual", c["accent"], self.on_accent,
                                 font=(UI, 9, "bold"))
            pill.pack(side="right", padx=(8, 8), pady=6)

        meta = b["hash"] + ("  " + b["subject"][:36] if b["subject"] else "")
        meta_lbl = ctk.CTkLabel(row, text=meta, font=(MONO, 9),
                                text_color=c["text_dim"], anchor="e", height=22)
        meta_lbl.pack(side="right", padx=(0, 10))

        name_lbl = ctk.CTkLabel(row, text=b["name"], font=(MONO, 11),
                                text_color=c["text"], anchor="w", height=22)
        name_lbl.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=4)

        for w in (row, name_lbl, meta_lbl):
            w.bind("<Button-1>", lambda _e, n=b["name"]: self._select_branch(n))
            w.bind("<Double-Button-1>", lambda _e, n=b["name"]: self._select_branch(n))
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
        if pill is not None:
            pill.bind("<Button-1>", lambda _e, n=b["name"]: self._select_branch(n))
            pill.bind("<Enter>", on_enter)
            pill.bind("<Leave>", on_leave)

        return {"frame": row, "name": name_lbl, "meta": meta_lbl}

    def _select_branch(self, name):
        self._branch_sel = name
        self._apply_branch_selection()

        current = next((b["name"] for b in self._branches if b["current"]), None)
        enabled = bool(name) and name != current
        self.branch_switch_btn.configure(state="normal" if enabled else "disabled")
        self.branch_delete_btn.configure(state="normal" if enabled else "disabled")

    def _apply_branch_selection(self):
        c = self.colors
        for name, parts in self._branch_rows.items():
            selected = name == self._branch_sel
            parts["frame"].configure(fg_color=c["panel"] if selected else "transparent")
            parts["name"].configure(text_color=c["accent"] if selected else c["text"])

    def _switch_branch(self):
        name = self._branch_sel
        if not name:
            self._set_footer("Selecione uma branch.", error=True)
            return

        def done(res):
            if self._is_result(res):
                ok, text = res
                self._set_footer(text, error=not ok)
            else:
                self._set_footer(f"Branch alterada para '{name}'.")
            self.refresh()

        self._run_bg(lambda: self.plugin.switch_branch(name), done,
                     busy=True, busy_msg=f"Trocando para '{name}'…")

    def _create_branch(self):
        name = self.new_branch_entry.get().strip()
        if not name:
            self._set_footer("Digite o nome da nova branch.", error=True)
            self.new_branch_entry.focus_set()
            return

        def done(res):
            if not self._is_result(res):
                return
            ok, text = res
            self._set_footer(text, error=not ok)
            if ok:
                self.new_branch_entry.delete(0, "end")
                self._branch_sel = name
            self.refresh()

        self._run_bg(lambda: self.plugin.create_branch(name, checkout=True), done,
                     busy=True, busy_msg=f"Criando '{name}'…")

    def _delete_branch(self):
        name = self._branch_sel
        if not name:
            return
        if not messagebox.askyesno(
            "Excluir branch",
            f"Deseja excluir a branch '{name}'?\n\n"
            "Se ela não estiver mesclada, o Git exige exclusão forçada.",
            parent=self.win,
        ):
            return

        def done(res):
            if not self._is_result(res):
                return
            ok, text = res
            if ok:
                self._set_footer(text)
                self._branch_sel = None
                self.refresh()
                return

            if "exclusão forçada" in text and messagebox.askyesno(
                "Branch não mesclada",
                f"{text}\n\nExcluir '{name}' mesmo assim?\n\n"
                "Aviso: commits exclusivos desta branch serão perdidos.",
                parent=self.win,
            ):
                self._run_bg(lambda: self.plugin.delete_branch(name, force=True),
                             forced_done, busy=True,
                             busy_msg=f"Excluindo '{name}' (forçado)…")
                return

            self._set_footer(text, error=True)

        def forced_done(res):
            if not self._is_result(res):
                return
            ok, text = res
            self._set_footer(text, error=not ok)
            if ok:
                self._branch_sel = None
            self.refresh()

        self._run_bg(lambda: self.plugin.delete_branch(name), done,
                     busy=True, busy_msg=f"Excluindo '{name}'…")

    def _reload_remote(self):
        if not self._alive():
            return
        c = self.colors
        info = self.plugin.get_remote_info()
        has_remote = bool(info)
        self._has_remote = has_remote
        if info:
            self.remote_title_lbl.configure(text=info.get("name") or "Remoto")
            self.remote_url_lbl.configure(text=info.get("url") or "")
        else:
            self.remote_title_lbl.configure(text="Nenhum remoto configurado")
            self.remote_url_lbl.configure(text="git remote add origin <url>")
        for btn in self.remote_btns.values():
            btn.configure(state="normal" if has_remote else "disabled")

        status = self.plugin.get_upstream_status()
        if status is None:
            self.remote_state_pill.configure(fg_color=c["panel_alt"])
            self.remote_state_lbl.configure(text="sem upstream", text_color=c["text_dim"])
        else:
            ahead, behind = status
            if not ahead and not behind:
                self.remote_state_pill.configure(fg_color=c["panel_alt"])
                self.remote_state_lbl.configure(text="sincronizado", text_color=c["add"])
            else:
                self.remote_state_pill.configure(fg_color=c["panel_alt"])
                self.remote_state_lbl.configure(
                    text=f"↑ {ahead}   ↓ {behind}",
                    text_color=c["mod"] if behind else c["add"],
                )

    def _remote_action(self, kind):
        if self._busy:
            return
        if not self._has_remote:
            self._set_footer("Nenhum remoto configurado.", error=True)
            return
        label = {"pull": "Pull", "push": "Push", "sync": "Sincronizar"}[kind]
        action = {
            "pull": self.plugin.git_pull,
            "push": self.plugin.git_push,
            "sync": self.plugin.git_sync,
        }[kind]

        self._log(f"→ git {kind}")
        self._set_busy(True, f"{label} em andamento…")

        def done(res):
            if not self._is_result(res):
                self._set_footer("Operação cancelada.", error=True)
                return
            ok, text = res
            self._log(("✓ " if ok else "✗ ") + text, "ok" if ok else "err")
            self._set_footer(text, error=not ok)
            self.refresh()

        action(on_done=done)

    def _log(self, message, tag="dim"):
        if not self._alive():
            return
        stamp = time.strftime("%H:%M:%S")
        box = self.log_box
        box.configure(state="normal")
        box.insert("end", f"[{stamp}] {message}\n", tag)
        total = int(box._textbox.index("end-1c").split(".")[0])
        if total > 300:
            box.delete("1.0", f"{total - 300}.0")
        box._textbox.see("end")
        box.configure(state="disabled")

    def _clear_log(self):
        if not self._alive():
            return
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def close(self):
        try:
            self.plugin._panel = None
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass
