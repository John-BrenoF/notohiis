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

        theme = AppContext().theme.get("editor", {})

        # Coluna 0: Gutter (Números de linha)
        self.line_numbers = tk.Canvas(self, width=45, bg=theme.get("gutter_bg", "#1e1e1e"), bd=0, highlightthickness=0)
        self.line_numbers.grid(row=0, column=0, sticky="ns")

        # Coluna 1: Git Margin (Indicadores de modificação)
        self.git_margin = tk.Canvas(self, width=15, bg=theme.get("gutter_bg", "#1e1e1e"), bd=0, highlightthickness=0)
        self.git_margin.grid(row=0, column=1, sticky="ns")

        # Coluna 2: Área de Texto Principal
        self.textbox = ctk.CTkTextbox(
            self, 
            undo=True, 
            font=("Consolas", 15), 
            corner_radius=0, 
            border_width=0,
            fg_color=theme.get("bg", "#1e1e1e"),
            text_color=theme.get("fg", "#d4d4d4")
        )
        self.textbox.grid(row=0, column=2, sticky="nsew")
        self.textbox._textbox.configure(insertbackground=theme.get("cursor", "white"), selectbackground=theme.get("selection_bg", "#264f78"))

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

        self.popup = None # Widget de sugestões

        # Inicializa tags de sintaxe se o plugin estiver carregado
        if AppContext().py_plugin:
            AppContext().py_plugin.setup_tags(self.textbox._textbox)

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

        # Regras de fechamento do popup
        if event and (event.keysym in ("Escape", "space", "Return") or event.type == "4"):
            self._hide_autocomplete()
        
        # Dispara realce de sintaxe Python
        if AppContext().py_plugin:
            AppContext().py_plugin.highlight()
            self._trigger_autocomplete(event)

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
            color = AppContext().theme.get("editor", {}).get("gutter_fg", "#858585")
            self.line_numbers.create_text(40, y, anchor="ne", text=linenum, fill=color, font=("Consolas", 11))
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

    def _trigger_autocomplete(self, event=None):
        """Consulta o core e decide se mostra o popup."""
        if not event or len(event.keysym) > 1 and event.keysym != "BackSpace":
            return

        ctx = AppContext()
        index = self.textbox.index(tk.INSERT)
        line, col = map(int, index.split("."))
        
        suggestions = ctx.autocomplete_engine.get_suggestions(self.get_text(), line, col)

        if suggestions:
            self._show_autocomplete_popup(suggestions)
        else:
            self._hide_autocomplete()

    def _show_autocomplete_popup(self, suggestions):
        self._hide_autocomplete()
        
        # Localiza as coordenadas X,Y do cursor de texto na tela
        pos = self.textbox._textbox.bbox(tk.INSERT)
        if not pos: return
        
        x, y, _, h = pos
        root_x = self.textbox._textbox.winfo_rootx() + x
        root_y = self.textbox._textbox.winfo_rooty() + y + h

        self.popup = tk.Listbox(
            self.master, 
            height=min(len(suggestions), 8),
            bg=AppContext().theme.get("sidebar", {}).get("bg", "#21252b"),
            fg=AppContext().theme.get("editor", {}).get("fg", "#abb2bf"),
            selectbackground=AppContext().theme.get("editor", {}).get("selection_bg", "#3e4451"),
            borderwidth=1, highlightthickness=0
        )
        for s in suggestions: self.popup.insert(tk.END, s)
        
        # Posiciona o popup logo abaixo do cursor
        self.popup.place(x=root_x - self.winfo_rootx(), y=root_y - self.winfo_rooty())
        self.popup.bind("<Button-1>", self._on_suggestion_select)

    def _hide_autocomplete(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _on_suggestion_select(self, event):
        if not self.popup: return
        selection = self.popup.get(self.popup.curselection())
        # Substitui o prefixo pela palavra completa
        self.textbox._textbox.delete("insert wordstart", tk.INSERT)
        self.textbox.insert(tk.INSERT, selection)
        self._hide_autocomplete()

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