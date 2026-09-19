#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

"""
Terminal Plugin para o Notohiis.
Suporta bash, zsh e fish com detecção automática, cópia/colagem,
zoom de fonte, menu de contexto e detecção de URLs clicáveis.
"""

import fcntl
import os
import pty
import re
import select
import shutil
import struct
import tempfile
import threading
import subprocess
import termios
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
import pyte
from core.src.app_context import AppContext
from core.src.session import SessionManager

# ── Constantes ──────────────────────────────────────────────────────────

HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
EXIT_RE = re.compile(rb"\x1b\]133;D;?(\d*)?(?:\x07|\x1b\\)")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)")

BASE_COLORS = {
    "black": "#1e1e1e", "red": "#cd3131", "green": "#0dbc79",
    "brown": "#e5e510", "blue": "#2472c8", "magenta": "#bc3fbc",
    "cyan": "#11a8cd", "white": "#e5e5e5",
}

BRIGHT_COLORS = {
    "black": "#666666", "red": "#f14c4c", "green": "#23d18b",
    "brown": "#f5f543", "blue": "#3b8eea", "magenta": "#d670d6",
    "cyan": "#29b8db", "white": "#ffffff",
}

# Hooks por shell para rastrear exit code (protocolo裁pjet裁133)
SHELL_HOOKS = {
    "bash": "PROMPT_COMMAND='__ec=$?; printf \"\\033]133;D;%s\\007\" \"$__ec\"'\n",
    "zsh": "precmd() { local __ec=$?; printf '\\033]133;D;%s\\007' \"$__ec\" }\n",
    "fish": (
        "function __nth_hook --on-event fish_prompt\n"
        "    set -l last_status $status\n"
        '    printf "\\033]133;D;%s\\007" "$last_status"\n'
        "end\n"
    ),
}

FONT_CANDIDATES = (
    "Consolas", "DejaVu Sans Mono", "Liberation Mono",
    "Ubuntu Mono", "Noto Sans Mono", "JetBrains Mono",
    "Fira Code", "Courier New", "Courier",
)

KEY_SEQUENCES = {
    "Return": b"\r",
    "BackSpace": b"\x7f",
    "Tab": b"\t",
    "Left": b"\x1b[D",
    "Right": b"\x1b[C",
    "Up": b"\x1b[A",
    "Down": b"\x1b[B",
    "Home": b"\x1b[H",
    "End": b"\x1b[F",
    "Delete": b"\x1b[3~",
    "Escape": b"\x1b",
    "Prior": b"\x1b[5~",     # Page Up
    "Next": b"\x1b[6~",      # Page Down
}

MODIFIER_KEYSYMS = frozenset((
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Alt_L", "Alt_R", "Caps_Lock", "Super_L", "Super_R",
))

# Ctrl+key mapeados (para keysyms comuns do terminal)
CTRL_MAP = {
    "a": b"\x01", "b": b"\x02", "c": b"\x03", "d": b"\x04",
    "e": b"\x05", "f": b"\x06", "g": b"\x07", "h": b"\x08",
    "i": b"\x09", "j": b"\x0a", "k": b"\x0b", "l": b"\x0c",
    "m": b"\x0d", "n": b"\x0e", "o": b"\x0f", "p": b"\x10",
    "q": b"\x11", "r": b"\x12", "s": b"\x13", "t": b"\x14",
    "u": b"\x15", "v": b"\x16", "w": b"\x17", "x": b"\x18",
    "y": b"\x19", "z": b"\x1a",
    "[": b"\x1b", "\\": b"\x1c", "]": b"\x1d", "^": b"\x1e", "_": b"\x1f",
}

DEFAULT_FG = "#f8f8f2"
DEFAULT_BG = "#0d0f12"
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 30
DEFAULT_FONT_SIZE = 12


# ── Utilitários de Shell ────────────────────────────────────────────────

def detect_shell() -> str:
    """Detecta o shell do usuário e retorna o caminho."""
    return os.environ.get("SHELL", "/bin/bash")


def get_shell_name(shell_path: str) -> str:
    """Extrai o nome do shell a partir do caminho."""
    return os.path.basename(shell_path).lower()


def build_shell_args(shell_path: str, env: dict) -> tuple:
    """Constrói argumentos de inicialização e caminhos temporários para o shell.
    
    Retorna: (args_list, env_dict, temp_paths_list)
    """
    name = get_shell_name(shell_path)
    temp_paths = []

    if "bash" in name:
        fd, path = tempfile.mkstemp(prefix="nth_bash_", suffix=".bash")
        with os.fdopen(fd, "w") as f:
            f.write('[ -f ~/.bashrc ] && source ~/.bashrc\n')
            f.write(SHELL_HOOKS["bash"])
        temp_paths.append(path)
        return [shell_path, "--rcfile", path, "-i"], env, temp_paths

    if "zsh" in name:
        tempdir = tempfile.mkdtemp(prefix="nth_zsh_")
        orig_zdotdir = env.get("ZDOTDIR", os.path.expanduser("~"))
        rc_path = os.path.join(tempdir, ".zshrc")
        with open(rc_path, "w") as f:
            f.write(f'[ -f "{orig_zdotdir}/.zshrc" ] && source "{orig_zdotdir}/.zshrc"\n')
            f.write(SHELL_HOOKS["zsh"])
        env["ZDOTDIR"] = tempdir
        temp_paths.append(tempdir)
        return [shell_path, "-i"], env, temp_paths

    if "fish" in name:
        # Fish usa config.d para hooks - cria um arquivo temporário
        config_dir = tempfile.mkdtemp(prefix="nth_fish_")
        confd = os.path.join(config_dir, "conf.d")
        os.makedirs(confd, exist_ok=True)
        hook_path = os.path.join(confd, "nth_hook.fish")
        with open(hook_path, "w") as f:
            f.write(SHELL_HOOKS["fish"])
        orig_xdg = env.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        orig_fish_config = os.path.join(orig_xdg, "fish", "config.fish")
        config_path = os.path.join(config_dir, "config.fish")
        with open(config_path, "w") as f:
            f.write(f'if test -f "{orig_fish_config}"\n')
            f.write(f'    source "{orig_fish_config}"\n')
            f.write("end\n")
        env["XDG_CONFIG_HOME"] = config_dir
        temp_paths.append(config_dir)
        return [shell_path], env, temp_paths

    # Shell desconhecido - inicia sem hooks
    return [shell_path], env, temp_paths


def cleanup_temp_paths(paths: list):
    """Remove arquivos e diretórios temporários de forma segura."""
    for path in paths:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        except OSError:
            pass


def pick_monospace_font() -> str:
    """Seleciona a melhor fonte monospace disponível no sistema."""
    try:
        available = set(tkfont.families())
    except Exception:
        return "Courier"
    for name in FONT_CANDIDATES:
        if name in available:
            return name
    try:
        return tkfont.nametofont("TkFixedFont").actual("family")
    except Exception:
        return "Courier"


# ── Plugin Principal ────────────────────────────────────────────────────

class TerminalPlugin:
    """Terminal integrado com suporte a múltiplos shells."""

    def __init__(self, ctx):
        self.ctx = ctx

        # Widgets
        self.term_frame = None
        self.header = None
        self.status_dot = None
        self.status_label = None
        self.output_text = None
        self.status_bar_btn = None

        # Processo PTY
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.reader_thread = None
        self.shell_path = None
        self.shell_name = None

        # pyte screen
        self.screen = None
        self.stream = None

        # Estado
        self.temp_paths = []
        self.font_family = None
        self.font_size = DEFAULT_FONT_SIZE
        self.default_fg = DEFAULT_FG
        self.default_bg = DEFAULT_BG
        self._stop = threading.Event()
        self._render_lock = threading.RLock()
        self._render_scheduled = False
        self._scroll_offset = 0
        self._tag_cache = {}
        self._fonts = {}
        self._cursor_visible = True
        self._resize_timer = None
        self._selection_start = None

        self._bind_shortcut()
        self._prepare_layout()

    # ── Atalhos e Layout ────────────────────────────────────────────────

    def _bind_shortcut(self):
        window = getattr(self.ctx, "window", None)
        if window:
            window.bind_all("<Control-j>", self.toggle_terminal, add="+")
            window.bind_all("<Control-J>", self.toggle_terminal, add="+")

    def _prepare_layout(self):
        window = getattr(self.ctx, "window", None)
        if not window:
            return
        window.grid_rowconfigure(2, weight=0)
        window.grid_rowconfigure(3, weight=0)
        window.grid_rowconfigure(4, weight=0)
        if hasattr(self.ctx, "status_bar") and self.ctx.status_bar:
            self.ctx.status_bar.grid(row=3, column=1, sticky="ew")
            self._add_status_bar_button(self.ctx.status_bar)
        if hasattr(self.ctx, "search_bar") and self.ctx.search_bar:
            self._patch_search_bar()

    def _patch_search_bar(self):
        search_bar = self.ctx.search_bar
        if not search_bar:
            return

        def patched_show(event=None):
            self.ctx.window.grid_rowconfigure(4, weight=0)
            search_bar.grid(row=4, column=1, sticky="ew")
            if hasattr(search_bar, "entry"):
                search_bar.entry.focus_set()

        search_bar.show = patched_show

    def _add_status_bar_button(self, status_bar):
        theme = AppContext().theme.get("status_bar", {})
        fg = theme.get("fg", "#9da5b4")
        hover_color = theme.get("hover", "#2c313a")

        btn = ctk.CTkButton(
            status_bar,
            text=">_ Terminal",
            font=("Segoe UI", 11),
            text_color=fg,
            fg_color="transparent",
            hover_color=hover_color,
            command=self.toggle_terminal,
            width=0,
        )
        btn.pack(side="left", padx=(2, 10))
        self.status_bar_btn = btn
        self._patch_status_bar_theme(status_bar)

    def _patch_status_bar_theme(self, status_bar):
        original_apply_theme = status_bar.apply_theme

        def patched_apply_theme():
            original_apply_theme()
            theme = AppContext().theme.get("status_bar", {})
            if self.status_bar_btn and self.status_bar_btn.winfo_exists():
                self.status_bar_btn.configure(
                    text_color=theme.get("fg", "#9da5b4"),
                    hover_color=theme.get("hover", "#2c313a"),
                )

        status_bar.apply_theme = patched_apply_theme

    # ── Toggle / Show / Hide ────────────────────────────────────────────

    def toggle_terminal(self, event=None):
        if self.term_frame is not None and self.term_frame.winfo_exists():
            self.hide_terminal()
        else:
            self.show_terminal()
        return "break"

    def show_terminal(self):
        window = getattr(self.ctx, "window", None)
        if not window:
            return

        self.font_family = pick_monospace_font()
        self.screen = pyte.HistoryScreen(80, 24, history=5000, ratio=0.4)
        self.stream = pyte.ByteStream(self.screen)
        self._tag_cache = {}
        self._fonts = {}
        self._scroll_offset = 0

        # ── Frame principal ─────────────────────────────────────────────
        self.term_frame = ctk.CTkFrame(window, corner_radius=0, fg_color=self.default_bg)
        self.term_frame.grid(row=2, column=1, sticky="nsew")
        window.grid_rowconfigure(2, minsize=260, weight=0)
        self.term_frame.grid_rowconfigure(0, weight=0)
        self.term_frame.grid_rowconfigure(1, weight=1)
        self.term_frame.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────
        self.header = ctk.CTkFrame(self.term_frame, height=26, corner_radius=0, fg_color="#161819")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.header, text="TERMINAL",
            font=(self.font_family, 10), text_color="#8a8f98",
        )
        title.grid(row=0, column=0, sticky="w", padx=8, pady=3)

        self.status_dot = ctk.CTkFrame(
            self.header, width=10, height=10, corner_radius=5, fg_color="#666666",
        )
        self.status_dot.grid(row=0, column=1, sticky="e", pady=8, padx=(0, 4))

        self.status_label = ctk.CTkLabel(
            self.header, text="", font=(self.font_family, 10),
            text_color="#8a8f98", width=28,
        )
        self.status_label.grid(row=0, column=2, sticky="e", padx=(0, 8), pady=3)

        # ── Área de texto ───────────────────────────────────────────────
        self.output_text = tk.Text(
            self.term_frame,
            bg=self.default_bg, fg=self.default_fg,
            insertbackground=self.default_fg,
            font=(self.font_family, self.font_size),
            wrap="none", undo=False,
            borderwidth=0, highlightthickness=0,
            state="disabled",
            spacing1=0, spacing3=0,
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.output_text.tag_configure("cursor", background=self.default_fg, foreground=self.default_bg)
        self.output_text.tag_configure("url", foreground="#569cd6", underline=True)

        self._setup_bindings()
        self.spawn_shell()
        self.output_text.focus_set()
        self.term_frame.after(500, self._blink)

    def hide_terminal(self):
        if self._resize_timer and self.term_frame:
            self.term_frame.after_cancel(self._resize_timer)
            self._resize_timer = None

        window = getattr(self.ctx, "window", None)
        if window:
            window.grid_rowconfigure(2, minsize=0, weight=0)
        self._cleanup_shell()
        if self.term_frame is not None:
            try:
                self.term_frame.destroy()
            except tk.TclError:
                pass
        self.term_frame = None
        self.header = None
        self.status_dot = None
        self.status_label = None
        self.output_text = None

    # ── Bindings ────────────────────────────────────────────────────────

    def _setup_bindings(self):
        """Registra todos os bindings do terminal."""
        tw = self.output_text

        # Teclado
        tw.bind("<Key>", self._on_key, add="+")
        tw.bind("<Button-1>", self._on_left_click, add="+")
        tw.bind("<Button-3>", self._on_right_click, add="+")

        # Scroll
        tw.bind("<MouseWheel>", self._on_mousewheel, add="+")
        tw.bind("<Button-4>", self._on_mousewheel, add="+")
        tw.bind("<Button-5>", self._on_mousewheel, add="+")
        tw.bind("<Shift-Prior>", lambda e: self._scroll_view(10), add="+")
        tw.bind("<Shift-Next>", lambda e: self._scroll_view(-10), add="+")

        # Zoom com Ctrl+/- e Ctrl+0
        tw.bind("<Control-plus>", self._zoom_in, add="+")
        tw.bind("<Control-equal>", self._zoom_in, add="+")
        tw.bind("<Control-minus>", self._zoom_out, add="+")
        tw.bind("<Control-0>", self._zoom_reset, add="+")

        # Cópia/Colagem
        tw.bind("<Control-Shift-C>", self._copy_selection, add="+")
        tw.bind("<Control-Shift-c>", self._copy_selection, add="+")
        tw.bind("<Control-Shift-V>", self._paste_clipboard, add="+")
        tw.bind("<Control-Shift-v>", self._paste_clipboard, add="+")

        # Redimensionamento
        self.term_frame.bind("<Configure>", self._on_resize, add="+")

    # ── Processo PTY ────────────────────────────────────────────────────

    def spawn_shell(self):
        if self.process:
            return

        shell = detect_shell()
        self.shell_path = shell
        self.shell_name = get_shell_name(shell)
        args, env, temp_paths = self._build_shell_launch(shell)
        self.temp_paths = temp_paths
        self.master_fd, self.slave_fd = pty.openpty()

        cwd = SessionManager.load_session()
        if not cwd or not os.path.isdir(cwd):
            cwd = None

        try:
            self._set_pty_size(self.master_fd, 24, 80)
            self.process = subprocess.Popen(
                args,
                stdin=self.slave_fd, stdout=self.slave_fd, stderr=self.slave_fd,
                close_fds=True, preexec_fn=os.setsid,
                env=env, cwd=cwd,
            )
        except Exception as exc:
            self._write_status_text(f"Falha ao iniciar shell ({shell}): {exc}\n")
            self._safe_close(self.master_fd)
            self._safe_close(self.slave_fd)
            self.master_fd = None
            self.slave_fd = None
            self.process = None
            cleanup_temp_paths(self.temp_paths)
            self.temp_paths = []
            return

        self._safe_close(self.slave_fd)
        self.slave_fd = None

        self._stop.clear()
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

        # Atualiza título do header
        if self.header:
            for child in self.header.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("text") == "TERMINAL":
                    child.configure(text=f"TERMINAL — {self.shell_name}")
                    break

    def _build_shell_launch(self, shell):
        env = os.environ.copy()
        return build_shell_args(shell, env)

    @staticmethod
    def _safe_close(fd):
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass

    def _set_pty_size(self, fd, rows, cols):
        try:
            tiocswinsz = getattr(termios, "TIOCSWINSZ", 0x5414)
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, tiocswinsz, winsize)
        except Exception:
            pass

    # ── Leitura de Output ───────────────────────────────────────────────

    def _read_output(self):
        if self.master_fd is None:
            return
        process = self.process
        while not self._stop.is_set() and process and process.poll() is None:
            try:
                rlist, _, _ = select.select([self.master_fd], [], [], 0.1)
            except (OSError, ValueError):
                break
            if self.master_fd in rlist:
                try:
                    data = os.read(self.master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                self._on_output(data)
        if process and self.term_frame and self.term_frame.winfo_exists():
            code = process.poll()
            if code is not None:
                self.term_frame.after(0, lambda: self._write_status_text(f"\n[{self.shell_name or 'shell'}] encerrado ({code})\n"))

    def _on_output(self, data):
        for match in EXIT_RE.finditer(data):
            group = match.group(1)
            code = int(group) if group else 0
            if self.term_frame and self.term_frame.winfo_exists():
                self.term_frame.after(0, lambda c=code: self._update_status(c))
        schedule = False
        with self._render_lock:
            if self.stream:
                self.stream.feed(data)
            if not self._render_scheduled:
                self._render_scheduled = True
                schedule = True
        if schedule and self.term_frame and self.term_frame.winfo_exists():
            self.term_frame.after(12, self._render)

    def _update_status(self, code):
        if not self.status_dot or not self.status_dot.winfo_exists():
            return
        color = "#23d18b" if code == 0 else "#f14c4c"
        self.status_dot.configure(fg_color=color)
        self.status_label.configure(text=str(code))

    def _write_status_text(self, text):
        if not self.output_text or not self.output_text.winfo_exists():
            return
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    # ── Renderização ────────────────────────────────────────────────────

    def _font_for(self, bold, italic):
        key = (bold, italic)
        font = self._fonts.get(key)
        if font:
            return font
        font = tkfont.Font(
            family=self.font_family,
            size=self.font_size,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman",
        )
        self._fonts[key] = font
        return font

    def _resolve_color(self, value, bold, is_fg):
        if not value or value == "default":
            return None
        if HEX_RE.match(value):
            return "#" + value
        table = BRIGHT_COLORS if (bold and is_fg) else BASE_COLORS
        return table.get(value)

    def _tag_for(self, char):
        fg = self._resolve_color(char.fg, char.bold, True) or self.default_fg
        bg = self._resolve_color(char.bg, False, False) or self.default_bg
        if char.reverse:
            fg, bg = bg, fg
        key = (fg, bg, char.bold, char.italics, char.underscore, char.strikethrough)
        name = self._tag_cache.get(key)
        if name:
            return name
        name = f"s{len(self._tag_cache)}"
        font = self._font_for(char.bold, char.italics)
        self.output_text.tag_configure(
            name, foreground=fg, background=bg, font=font,
            underline=char.underscore, overstrike=char.strikethrough,
        )
        self._tag_cache[key] = name
        return name

    @staticmethod
    def _same_style(a, b):
        return (
            a.fg == b.fg and a.bg == b.bg and a.bold == b.bold
            and a.italics == b.italics and a.underscore == b.underscore
            and a.strikethrough == b.strikethrough and a.reverse == b.reverse
        )

    def _render(self):
        if not self.output_text or not self.output_text.winfo_exists():
            return
        with self._render_lock:
            self._render_scheduled = False
            if not self.screen:
                return
            rows = self.screen.lines
            cols = self.screen.columns
            cursor_x, cursor_y = self.screen.cursor.x, self.screen.cursor.y
            cursor_hidden = self.screen.cursor.hidden
            offset = self._scroll_offset

            if offset:
                history = list(self.screen.history.top)
                total = len(history)
                start = max(total - offset, 0)
                end = min(start + rows, total)
                segment = history[start:end]
                remaining = rows - len(segment)
                display_rows = segment + [self.screen.buffer[i] for i in range(remaining)]
            else:
                display_rows = [self.screen.buffer[i] for i in range(rows)]

            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            for row in display_rows:
                x = 0
                while x < cols:
                    char = row[x]
                    seg = char.data or " "
                    tag = self._tag_for(char)
                    x += 1
                    while x < cols and self._same_style(row[x], char):
                        seg += row[x].data or " "
                        x += 1
                    self.output_text.insert("end", seg, tag)
                self.output_text.insert("end", "\n")
            self.output_text.configure(state="disabled")

            self.output_text.tag_remove("cursor", "1.0", "end")
            if not offset and not cursor_hidden:
                idx = f"{cursor_y + 1}.{cursor_x}"
                self.output_text.tag_add("cursor", idx, f"{idx}+1c")

    # ── Cursor Blink ────────────────────────────────────────────────────

    def _blink(self):
        if not self.term_frame or not self.term_frame.winfo_exists():
            return
        self._cursor_visible = not self._cursor_visible
        if self.output_text and self.output_text.winfo_exists():
            if self._cursor_visible:
                self.output_text.tag_configure("cursor", background=self.default_fg, foreground=self.default_bg)
            else:
                self.output_text.tag_configure("cursor", background=self.default_bg, foreground=self.default_fg)
        self.term_frame.after(500, self._blink)

    # ── Scroll ──────────────────────────────────────────────────────────

    def _scroll_view(self, lines):
        with self._render_lock:
            if not self.screen:
                return "break"
            max_offset = len(self.screen.history.top)
            self._scroll_offset = max(0, min(self._scroll_offset + lines, max_offset))
        self._render()
        return "break"

    def _on_mousewheel(self, event):
        delta = 0
        if getattr(event, "delta", 0):
            delta = 3 if event.delta > 0 else -3
        elif getattr(event, "num", None) == 4:
            delta = 3
        elif getattr(event, "num", None) == 5:
            delta = -3
        if delta == 0:
            return "break"
        return self._scroll_view(delta)

    # ── Resize ──────────────────────────────────────────────────────────

    def _on_resize(self, event=None):
        if getattr(self, '_resize_timer', None) and self.term_frame:
            self.term_frame.after_cancel(self._resize_timer)
        if self.term_frame:
            self._resize_timer = self.term_frame.after(150, self._apply_resize)

    def _apply_resize(self):
        if not self.output_text or self.master_fd is None or not self.screen:
            return

        width = self.output_text.winfo_width()
        height = self.output_text.winfo_height()
        if width <= 1 or height <= 1:
            return

        font = self._font_for(False, False)
        char_w = max(font.measure("0"), 1)
        char_h = max(font.metrics("linespace"), 1)
        cols = max(width // char_w, 10)
        rows = max(height // char_h, 3)

        with self._render_lock:
            if (cols, rows) == (self.screen.columns, self.screen.lines):
                return
            self.screen.resize(lines=rows, columns=cols)

        self._set_pty_size(self.master_fd, rows, cols)
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), 28)  # SIGWINCH
            except Exception:
                pass
        self._render()

    # ── Input de Teclado ────────────────────────────────────────────────

    def _on_key(self, event):
        if self.master_fd is None:
            return "break"

        # Sai do scroll ao digitar
        if self._scroll_offset:
            self._scroll_offset = 0
            self._render()

        key = event.keysym
        ctrl_pressed = bool(event.state & 0x4)
        shift_pressed = bool(event.state & 0x1)

        # ── Ctrl+Shift+Key (cópia/colagem do sistema) ──────────────────
        if ctrl_pressed and shift_pressed:
            return "break"  # Deixa o binding dedicado tratar

        # ── Sequências de teclas especiais ──────────────────────────────
        if key in KEY_SEQUENCES:
            seq = KEY_SEQUENCES[key]
        elif key in MODIFIER_KEYSYMS:
            return "break"
        else:
            char = event.char
            if not char:
                return "break"

            # Ctrl+key: mapeia para código de controle (0x01-0x1a)
            if ctrl_pressed:
                lower = char.lower()
                if lower in CTRL_MAP:
                    seq = CTRL_MAP[lower]
                elif len(char) == 1 and ord(char) < 32:
                    seq = char.encode("latin-1", errors="replace")
                else:
                    return "break"
            else:
                seq = char.encode(errors="replace")

        try:
            os.write(self.master_fd, seq)
        except OSError:
            pass
        return "break"

    # ── Click ───────────────────────────────────────────────────────────

    def _on_left_click(self, event):
        """Foco ao clicar e detecção de URL."""
        self.output_text.focus_set()

        # Verifica se clicou em uma URL
        try:
            index = self.output_text.index(f"@{event.x},{event.y}")
            line = self.output_text.get(f"{index} linestart", f"{index} lineend")

            # Busca URLs na linha
            for match in URL_RE.finditer(line):
                start_col = match.start()
                end_col = match.end()
                start_idx = f"{index.split('.')[0]}.{start_col}"
                end_idx = f"{index.split('.')[0]}.{end_col}"

                # Verifica se o click está dentro da URL
                click_col = int(index.split('.')[1])
                if start_col <= click_col <= end_col:
                    import webbrowser
                    webbrowser.open(match.group())
                    return
        except Exception:
            pass

    def _on_right_click(self, event):
        """Menu de contexto do terminal."""
        menu = tk.Menu(self.output_text, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)

        # Opções de seleção
        menu.add_command(label="📋 Copiar (Ctrl+Shift+C)", command=self._copy_selection)
        menu.add_command(label="📄 Colar (Ctrl+Shift+V)", command=self._paste_clipboard)
        menu.add_separator()
        menu.add_command(label="🔍 Selecionar Tudo", command=self._select_all)
        menu.add_separator()

        # Zoom
        menu.add_command(label="🔎 Aumentar Fonte (Ctrl+)", command=self._zoom_in)
        menu.add_command(label="缩小 Diminuir Fonte (Ctrl+-)", command=self._zoom_out)
        menu.add_command(label="↺ Tamanho Padrão (Ctrl+0)", command=self._zoom_reset)
        menu.add_separator()

        # Shell
        menu.add_command(label="🔄 Reiniciar Shell", command=self._restart_shell)
        menu.add_command(label="✕ Fechar Terminal", command=self.hide_terminal)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ── Cópia / Colagem ─────────────────────────────────────────────────

    def _copy_selection(self, event=None):
        """Copia a seleção atual para o clipboard do sistema."""
        try:
            if self.output_text.tag_ranges(tk.SEL):
                text = self.output_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.output_text.clipboard_clear()
                self.output_text.clipboard_append(text)
        except tk.TclError:
            pass
        return "break"

    def _paste_clipboard(self, event=None):
        """Cola o conteúdo do clipboard para o shell."""
        try:
            text = self.output_text.clipboard_get()
        except tk.TclError:
            return "break"

        if not text or self.master_fd is None:
            return "break"

        # Sai do scroll
        if self._scroll_offset:
            self._scroll_offset = 0
            self._render()

        # Envia cada linha separadamente (enter no final de cada uma)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            try:
                os.write(self.master_fd, line.encode(errors="replace"))
                if i < len(lines) - 1:
                    os.write(self.master_fd, b"\r")
            except OSError:
                break
        return "break"

    def _select_all(self):
        """Seleciona todo o texto do terminal."""
        self.output_text.configure(state="normal")
        self.output_text.tag_add(tk.SEL, "1.0", "end-1c")
        self.output_text.configure(state="disabled")

    # ── Zoom de Fonte ───────────────────────────────────────────────────

    def _zoom_in(self, event=None):
        """Aumenta o tamanho da fonte."""
        if self.font_size < MAX_FONT_SIZE:
            self.font_size += 1
            self._apply_font_change()
        return "break"

    def _zoom_out(self, event=None):
        """Diminui o tamanho da fonte."""
        if self.font_size > MIN_FONT_SIZE:
            self.font_size -= 1
            self._apply_font_change()
        return "break"

    def _zoom_reset(self, event=None):
        """Reseta o tamanho da fonte para o padrão."""
        self.font_size = DEFAULT_FONT_SIZE
        self._apply_font_change()
        return "break"

    def _apply_font_change(self):
        """Aplica a mudança de fonte e re-renderiza."""
        self._fonts.clear()
        self._tag_cache.clear()
        if self.output_text:
            self.output_text.configure(font=(self.font_family, self.font_size))
        self._on_resize()

    # ── Reiniciar Shell ─────────────────────────────────────────────────

    def _restart_shell(self):
        """Reinicia o shell atual."""
        self._cleanup_shell()
        if self.screen:
            self.screen.reset()
        self._tag_cache = {}
        self._fonts = {}
        self._scroll_offset = 0
        self.spawn_shell()
        self._render()

    # ── Limpeza ─────────────────────────────────────────────────────────

    def _cleanup_shell(self):
        self._stop.set()

        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1.0)
        self.reader_thread = None

        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), 9)
            except Exception:
                pass
            try:
                self.process.wait(timeout=1.0)
            except Exception:
                pass
            self.process = None

        with self._render_lock:
            self._safe_close(self.master_fd)
            self.master_fd = None
            self._safe_close(self.slave_fd)
            self.slave_fd = None
            self.screen = None
            self.stream = None

        cleanup_temp_paths(self.temp_paths)
        self.temp_paths = []

    def run(self):
        pass


def setup(ctx):
    plugin = TerminalPlugin(ctx)
    if hasattr(ctx, "external_plugins"):
        ctx.external_plugins.append(plugin)
