import os
import pty
import select
import threading
import subprocess
import customtkinter as ctk
from core.src.app_context import AppContext

class TerminalPlugin:
    def __init__(self, ctx):
        self.ctx = ctx
        self.term_frame = None
        self.output_text = None
        self.input_entry = None
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.reader_thread = None
        self._stop = False
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

    def toggle_terminal(self, event=None):
        if self.term_frame and self.term_frame.winfo_exists():
            self.hide_terminal()
        else:
            self.show_terminal()
        return "break"

    def show_terminal(self):
        if self.term_frame and self.term_frame.winfo_exists():
            self.term_frame.lift()
            self.output_text.focus_set()
            return

        window = getattr(self.ctx, "window", None)
        if not window:
            return

        self.term_frame = ctk.CTkFrame(window, corner_radius=0)
        self.term_frame.grid(row=2, column=1, sticky="nsew")
        window.grid_rowconfigure(2, minsize=240, weight=0)
        self.term_frame.grid_rowconfigure(0, weight=1)
        self.term_frame.grid_columnconfigure(0, weight=1)

        self.output_text = ctk.CTkTextbox(self.term_frame, corner_radius=0)
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.output_text.configure(state="normal")
        self.output_text._textbox.bind("<Key>", self._on_key, add="+")
        self.output_text._textbox.bind("<Button-1>", lambda e: self.output_text.focus_set(), add="+")
        self.spawn_shell()
        self.output_text.focus_set()

    def hide_terminal(self):
        if self.term_frame and self.term_frame.winfo_exists():
            self.term_frame.grid_forget()
        self._cleanup_shell()

    def spawn_shell(self):
        if self.process:
            return
        shell = os.environ.get("SHELL", "/bin/bash")
        self.master_fd, self.slave_fd = pty.openpty()
        try:
            self.process = subprocess.Popen([shell], stdin=self.slave_fd, stdout=self.slave_fd, stderr=self.slave_fd, close_fds=True, preexec_fn=os.setsid)
        except Exception:
            self.master_fd = None
            self.slave_fd = None
            self.process = None
            return
        self._stop = False
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        self._append_output(f"Terminal iniciado: {shell}\n")

    def _read_output(self):
        if self.master_fd is None:
            return
        while not self._stop and self.process and self.process.poll() is None:
            rlist, _, _ = select.select([self.master_fd], [], [], 0.1)
            if self.master_fd in rlist:
                try:
                    data = os.read(self.master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                text = data.decode(errors="replace")
                if self.term_frame and self.term_frame.winfo_exists():
                    self.term_frame.after(0, lambda t=text: self._append_output(t))
        if self.process and self.process.poll() is not None and self.term_frame and self.term_frame.winfo_exists():
            code = self.process.returncode
            self.term_frame.after(0, lambda: self._append_output(f"\nProcesso encerrado ({code})\n"))

    def _append_output(self, text):
        if not self.output_text:
            return
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def _on_key(self, event):
        if self.master_fd is None:
            return "break"
        key = event.keysym
        if key == "Return":
            seq = b"\r"
        elif key == "BackSpace":
            seq = b"\x7f"
        elif key == "Tab":
            seq = b"\t"
        elif key == "Left":
            seq = b"\x1b[D"
        elif key == "Right":
            seq = b"\x1b[C"
        elif key == "Up":
            seq = b"\x1b[A"
        elif key == "Down":
            seq = b"\x1b[B"
        elif key == "Home":
            seq = b"\x1b[H"
        elif key == "End":
            seq = b"\x1b[F"
        elif key == "Delete":
            seq = b"\x1b[3~"
        elif key == "Escape":
            seq = b"\x1b"
        else:
            char = event.char
            if not char:
                return "break"
            seq = char.encode(errors="replace")
        try:
            os.write(self.master_fd, seq)
        except OSError:
            pass
        return "break"

    def _send_interrupt(self, event=None):
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), 2)
            except Exception:
                pass
        return "break"

    def _cleanup_shell(self):
        self._stop = True
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), 9)
            except Exception:
                pass
            self.process = None
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None
        if self.slave_fd is not None:
            try:
                os.close(self.slave_fd)
            except Exception:
                pass
            self.slave_fd = None

    def run(self):
        pass


def setup(ctx):
    plugin = TerminalPlugin(ctx)
    if hasattr(ctx, "external_plugins"):
        ctx.external_plugins.append(plugin)
