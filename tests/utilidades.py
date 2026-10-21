import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EditorFake:

    def __init__(self, texto=""):
        self.text = texto
        self.cursor = "1.0"
        self.separadores = 0
        self.grupos = []
        self.resets = 0
        self.undos = 0
        self.redos = 0

    def get_text(self):
        return self.text

    def set_text(self, texto):
        self.text = texto

    def get_cursor_index(self):
        return self.cursor

    def reset_undo_stack(self):
        self.resets += 1

    def edit_separator(self):
        self.separadores += 1

    def begin_undo_group(self):
        self.grupos.append("begin")

    def end_undo_group(self):
        self.grupos.append("end")

    def undo(self):
        self.undos += 1

    def redo(self):
        self.redos += 1


def rodar_em_subprocesso(codigo, cwd=None, args=(), timeout=180):
    return subprocess.run(
        [sys.executable, "-c", codigo, *args],
        cwd=cwd or RAIZ,
        env=_ambiente(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def rodar_script(caminho, args=(), cwd=None, timeout=300):
    return subprocess.run(
        [sys.executable, caminho, *args],
        cwd=cwd or RAIZ,
        env=_ambiente(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _ambiente():
    env = os.environ.copy()
    env["PYTHONPATH"] = RAIZ + os.pathsep + env.get("PYTHONPATH", "")
    return env
