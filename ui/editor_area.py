import customtkinter as ctk
import tkinter as tk
from core.src.app_context import AppContext

class EditorArea(ctk.CTkFrame):
    """Widget principal de edição de texto com numeração de linhas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        
        self.line_numbers = tk.Canvas(self, width=40, bg='#1e1e1e', bd=0, highlightthickness=0)
        self.line_numbers.pack(side="left", fill="y")

        self.textbox = ctk.CTkTextbox(
            self, 
            undo=True, 
            font=("Consolas", 15), 
            corner_radius=0, 
            border_width=0
        )
        self.textbox.pack(side="right", fill="both", expand=True)

        self.textbox.bind("<KeyRelease>", self._on_event)
        self.textbox.bind("<ButtonRelease-1>", self._on_event)
        self.textbox.bind("<MouseWheel>", self._on_event)
        self.textbox._textbox.bind("<Configure>", self._on_event)
        self.textbox._textbox.bind("<Key>", self._set_dirty)

    def _set_dirty(self, event=None):
        AppContext().is_dirty = True

    def _on_event(self, event=None):
        self.redraw_line_numbers()
        self._update_status_bar()

    def redraw_line_numbers(self):
        self.line_numbers.delete("all")
        i = self.textbox.index("@0,0")
        while True :
            dline= self.textbox._textbox.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.line_numbers.create_text(35, y, anchor="ne", text=linenum, fill="#858585", font=("Consolas", 12))
            i = self.textbox.index("%s+1line" % i)

    def get_text(self) -> str:
        return self.textbox.get("1.0", tk.END)

    def set_text(self, text: str):
        self.textbox.delete("1.0", tk.END)
        self.textbox.insert("1.0", text)
        self.redraw_line_numbers()
        AppContext().is_dirty = False

    def _update_status_bar(self):
        ctx = AppContext()
        if ctx.status_bar:
            cursor_pos = self.textbox.index(ctk.INSERT).split(".")
            line = cursor_pos[0]
            col = cursor_pos[1]
            ctx.status_bar.update_status(line, col, ctx.current_file or "Novo Arquivo")
            if ctx.is_dirty:
                ctx.status_bar.file_label.configure(text=f"* {ctx.current_file or 'Novo Arquivo'}")