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

HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")
EXIT_RE = re.compile(rb"\x1b\]133;D;?(\d*)?(?:\x07|\x1b\\)")

BASE_COLORS = {
    "black": "#1e1e1e",
    "red": "#cd3131",
    "green": "#0dbc79",
    "brown": "#e5e510",
    "blue": "#2472c8",
    "magenta": "#bc3fbc",
    "cyan": "#11a8cd",
    "white": "#e5e5e5",
}

BRIGHT_COLORS = {
    "black": "#666666",
    "red": "#f14c4c",
    "green": "#23d18b",
    "brown": "#f5f543",
    "blue": "#3b8eea",
    "magenta": "#d670d6",
    "cyan": "#29b8db",
    "white": "#ffffff",
}

BASH_HOOK = "PROMPT_COMMAND='__ec=$?; printf \"\\033]133;D;%s\\007\" \"$__ec\"'\n"
ZSH_HOOK = "precmd() { local __ec=$?; printf '\\033]133;D;%s\\007' \"$__ec\" }\n"

FONT_CANDIDATES = (
    "Consolas", "DejaVu Sans Mono", "Liberation Mono",
    "Ubuntu Mono", "Noto Sans Mono", "Courier New", "Courier",
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
    "Prior": b"\x1b[5~",
    "Next": b"\x1b[6~",
}

MODIFIER_KEYSYMS = (
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Alt_L", "Alt_R", "Caps_Lock", "Super_L", "Super_R",
)


class TerminalPlugin:
    def __init__(self, ctx):
        self.ctx = ctx
        self.term_frame = None
        self.header = None
        self.status_dot = None
        self.status_label = None
        self.output_text = None
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.reader_thread = None
        self.shell_path = None
        self.screen = None
        self.stream = None
        self.temp_paths = []
        self.font_family = None
        self.font_size = 12
        self.default_fg = "#f8f8f2"
        self.default_bg = "#0d0f12"
        self._stop = threading.Event()
        self._render_lock = threading.RLock()
        self._render_scheduled = False
        self._scroll_offset = 0
        self._tag_cache = {}
        self._fonts = {}
        self._cursor_visible = True
        self.status_bar_btn = None
        self._bind_shortcut()
        self._prepare_layout()

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

        self.font_family = self._pick_monospace_font()
        self.screen = pyte.HistoryScreen(80, 24, history=5000, ratio=0.4)
        self.stream = pyte.ByteStream(self.screen)
        self._tag_cache = {}
        self._fonts = {}
        self._scroll_offset = 0

        self.term_frame = ctk.CTkFrame(window, corner_radius=0, fg_color=self.default_bg)
        self.term_frame.grid(row=2, column=1, sticky="nsew")
        window.grid_rowconfigure(2, minsize=260, weight=0)
        self.term_frame.grid_rowconfigure(0, weight=0)
        self.term_frame.grid_rowconfigure(1, weight=1)
        self.term_frame.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkFrame(self.term_frame, height=26, corner_radius=0, fg_color="#161819")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self.header, text="TERMINAL", font=(self.font_family, 10), text_color="#8a8f98")
        title.grid(row=0, column=0, sticky="w", padx=8, pady=3)

        self.status_dot = ctk.CTkFrame(self.header, width=10, height=10, corner_radius=5, fg_color="#666666")
        self.status_dot.grid(row=0, column=1, sticky="e", pady=8, padx=(0, 4))

        self.status_label = ctk.CTkLabel(self.header, text="", font=(self.font_family, 10), text_color="#8a8f98", width=28)
        self.status_label.grid(row=0, column=2, sticky="e", padx=(0, 8), pady=3)

        self.output_text = tk.Text(
            self.term_frame,
            bg=self.default_bg,
            fg=self.default_fg,
            insertbackground=self.default_fg,
            font=(self.font_family, self.font_size),
            wrap="none",
            undo=False,
            borderwidth=0,
            highlightthickness=0,
            state="disabled",
            spacing1=0,
            spacing3=0,
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.output_text.tag_configure("cursor", background=self.default_fg, foreground=self.default_bg)

        self.output_text.bind("<Key>", self._on_key, add="+")
        self.output_text.bind("<Button-1>", lambda e: self.output_text.focus_set(), add="+")
        self.output_text.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.output_text.bind("<Button-4>", self._on_mousewheel, add="+")
        self.output_text.bind("<Button-5>", self._on_mousewheel, add="+")
        self.output_text.bind("<Shift-Prior>", lambda e: self._scroll_view(10), add="+")
        self.output_text.bind("<Shift-Next>", lambda e: self._scroll_view(-10), add="+")
        self.term_frame.bind("<Configure>", self._on_resize, add="+")

        self.spawn_shell()
        self.output_text.focus_set()
        self.term_frame.after(500, self._blink)

    def hide_terminal(self):
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

    def _pick_monospace_font(self):
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

    def _build_shell_launch(self, shell):
        name = os.path.basename(shell)
        env = os.environ.copy()
        temp_paths = []

        if "bash" in name:
            fd, path = tempfile.mkstemp(prefix="term_rc_", suffix=".bash")
            with os.fdopen(fd, "w") as handle:
                handle.write('[ -f ~/.bashrc ] && source ~/.bashrc\n')
                handle.write(BASH_HOOK)
            temp_paths.append(path)
            return [shell, "--rcfile", path, "-i"], env, temp_paths

        if "zsh" in name:
            tempdir = tempfile.mkdtemp(prefix="term_zdot_")
            orig_zdotdir = env.get("ZDOTDIR", os.path.expanduser("~"))
            rc_path = os.path.join(tempdir, ".zshrc")
            with open(rc_path, "w") as handle:
                handle.write(f'[ -f "{orig_zdotdir}/.zshrc" ] && source "{orig_zdotdir}/.zshrc"\n')
                handle.write(ZSH_HOOK)
            env["ZDOTDIR"] = tempdir
            temp_paths.append(tempdir)
            return [shell, "-i"], env, temp_paths

        return [shell], env, temp_paths

    def _cleanup_temp_paths(self):
        for path in self.temp_paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except OSError:
                pass
        self.temp_paths = []

    def spawn_shell(self):
        if self.process:
            return
        shell = os.environ.get("SHELL", "/bin/bash")
        self.shell_path = shell
        args, env, temp_paths = self._build_shell_launch(shell)
        self.temp_paths = temp_paths
        self.master_fd, self.slave_fd = pty.openpty()
        try:
            self._set_pty_size(self.master_fd, 24, 80)
            self.process = subprocess.Popen(
                args,
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                close_fds=True,
                preexec_fn=os.setsid,
                env=env,
            )
        except Exception as exc:
            self._write_status_text(f"Falha ao iniciar shell: {exc}\n")
            self._safe_close(self.master_fd)
            self._safe_close(self.slave_fd)
            self.master_fd = None
            self.slave_fd = None
            self.process = None
            self._cleanup_temp_paths()
            return

        self._safe_close(self.slave_fd)
        self.slave_fd = None

        self._stop.clear()
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

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

    def _on_resize(self, event=None):
        if not self.output_text or self.master_fd is None or not self.screen:
            return
        font = self._font_for(False, False)
        char_w = max(font.measure("0"), 1)
        char_h = max(font.metrics("linespace"), 1)
        cols = max(self.output_text.winfo_width() // char_w, 10)
        rows = max(self.output_text.winfo_height() // char_h, 3)
        with self._render_lock:
            if (cols, rows) == (self.screen.columns, self.screen.lines):
                return
            self.screen.resize(lines=rows, columns=cols)
        self._set_pty_size(self.master_fd, rows, cols)
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), 28)
            except Exception:
                pass
        self._render()

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
                self.term_frame.after(0, lambda: self._write_status_text(f"\nProcesso encerrado ({code})\n"))

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
            name,
            foreground=fg,
            background=bg,
            font=font,
            underline=char.underscore,
            overstrike=char.strikethrough,
        )
        self._tag_cache[key] = name
        return name

    @staticmethod
    def _same_style(a, b):
        return (
            a.fg == b.fg
            and a.bg == b.bg
            and a.bold == b.bold
            and a.italics == b.italics
            and a.underscore == b.underscore
            and a.strikethrough == b.strikethrough
            and a.reverse == b.reverse
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

    def _on_key(self, event):
        if self.master_fd is None:
            return "break"

        if self._scroll_offset:
            self._scroll_offset = 0
            self._render()

        key = event.keysym
        ctrl_pressed = bool(event.state & 0x4)

        if key in KEY_SEQUENCES:
            seq = KEY_SEQUENCES[key]
        elif key in MODIFIER_KEYSYMS:
            return "break"
        else:
            char = event.char
            if not char:
                return "break"
            if ctrl_pressed and len(char) == 1 and ord(char) < 32:
                seq = char.encode("latin-1", errors="replace")
            else:
                seq = char.encode(errors="replace")

        try:
            os.write(self.master_fd, seq)
        except OSError:
            pass
        return "break"

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

        self._cleanup_temp_paths()

    def run(self):
        pass


def setup(ctx):
    plugin = TerminalPlugin(ctx)
    if hasattr(ctx, "external_plugins"):
        ctx.external_plugins.append(plugin)