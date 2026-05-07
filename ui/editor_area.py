import customtkinter as ctk
import tkinter as tk
from core.src.app_context import AppContext

class EditorArea(ctk.CTkFrame):
    """Widget principal de edição de texto com numeração de linhas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        
        # Configuração da Grade: Coluna 0 (Números), Coluna 1 (Git), Coluna 2 (Texto)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Coluna 0: Gutter (Números de linha)
        self.line_numbers = tk.Canvas(self, width=45, bg='#1e1e1e', bd=0, highlightthickness=0)
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        # Coluna 1: Git Margin (Indicadores de modificação)
        self.git_margin = tk.Canvas(self, width=15, bg='#1e1e1e', bd=0, highlightthickness=0)
        self.git_margin.grid(row=0, column=1, sticky="ns")

        # Coluna 2: Área de Texto Principal
        self.textbox = ctk.CTkTextbox(
            self, 
            undo=True, 
            font=("Consolas", 15), 
            corner_radius=0, 
            border_width=0
        )
        self.textbox.grid(row=0, column=2, sticky="nsew")

        # Sincronização de Scroll
        self.textbox._textbox.config(yscrollcommand=self._on_text_scroll)

        # Bindings
        self.textbox.bind("<KeyRelease>", self._on_event)
        self.textbox.bind("<ButtonRelease-1>", self._on_event)
        self.textbox.bind("<MouseWheel>", self._on_event)
        self.textbox._textbox.bind("<Configure>", self._on_event)
        self.textbox._textbox.bind("<Key>", self._set_dirty)

        self.line_numbers.bind("<MouseWheel>", self._on_canvas_mousewheel)
        self.git_margin.bind("<MouseWheel>", self._on_canvas_mousewheel)

    def _set_dirty(self, event=None):
        AppContext().is_dirty = True

    def _on_text_scroll(self, *args):
        """Callback for the textbox's yscrollcommand."""
        # The *args are typically (fraction_start, fraction_end) for an external scrollbar.
        self.redraw_line_numbers()
        self._update_status_bar()

    def _on_event(self, event=None):
        self.redraw_line_numbers()
        self._update_status_bar()

    def redraw_line_numbers(self):
        self.line_numbers.delete("all")

        # Get the first and last visible line numbers
        # Use dlineinfo to get the y-coordinate of the line
        # Iterate from the top of the textbox to the bottom
        i = self.textbox.index("@0,0") # Start from the top-left visible character
        while True:
            dline = self.textbox._textbox.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.line_numbers.create_text(40, y, anchor="ne", text=linenum, fill="#858585", font=("Consolas", 11))
            i = self.textbox.index(f"{i}+1line") # Move to the next line

    def get_text(self) -> str:
        # Tkinter Text widget always adds a newline at the end, so remove it if it's the only content
        content = self.textbox.get("1.0", tk.END)
        if content.endswith('\n') and len(content) == 1:
            return ""
        return self.textbox.get("1.0", tk.END)

    def set_text(self, text: str):
        self.textbox.delete("1.0", tk.END)
        self.textbox.insert("1.0", text)
        self.redraw_line_numbers()
        AppContext().is_dirty = False

    def _on_canvas_mousewheel(self, event):
        """Scroll the textbox when mouse wheel is used on the line numbers canvas."""
        if event.num == 4 or event.delta > 0: # Scroll up
            self.textbox._textbox.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0: # Scroll down
            self.textbox._textbox.yview_scroll(1, "units")
        # The textbox's yscrollcommand will trigger _on_text_scroll, which redraws line numbers and updates status.
        return "break" # Prevent event propagation to parent widgets

    def _update_status_bar(self):
        ctx = AppContext()
        if ctx.status_bar:
            cursor_pos = self.textbox.index(tk.INSERT).split(".")
            line = cursor_pos[0]
            col = cursor_pos[1]
            ctx.status_bar.update_status(line, col, ctx.current_file or "Novo Arquivo")
            if ctx.is_dirty:
                ctx.status_bar.file_label.configure(text=f"* {ctx.current_file or 'Novo Arquivo'}")
        
        # Atualizar visibilidade do botão Markdown
        if ctx.md_plugin:
            ctx.md_plugin.update_button_visibility(ctx.current_file)