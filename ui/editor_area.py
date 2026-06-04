import customtkinter as ctk
import tkinter as tk
from core.src.app_context import AppContext
from core.interfaces import TextEditor, EditorEvent

class EditorArea(ctk.CTkFrame, TextEditor):
    """Widget principal de edição de texto com numeração de linhas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self.ctx = AppContext()
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
        
        # Desabilita separadores automáticos para que o AppContext controle a granularidade
        self.textbox._textbox.configure(autoseparators=False)

        # Sincronização de Scroll
        self.textbox._textbox.config(yscrollcommand=self._on_text_scroll)

        # Bindings
        self.textbox.bind("<KeyRelease>", self._on_event)
        self.textbox.bind("<ButtonRelease-1>", self._on_event)
        self.textbox.bind("<MouseWheel>", self._on_event)
        self.textbox._textbox.bind("<KeyPress>", self._on_key_press, add="+")
        self.textbox._textbox.bind("<Control-a>", self._select_all)
        self.textbox._textbox.bind("<Control-Tab>", self._force_autocomplete)
        self.textbox._textbox.bind("<Configure>", self._on_event)
        self.textbox._textbox.bind("<Key>", self._set_dirty)

        self.line_numbers.bind("<MouseWheel>", self._on_canvas_mousewheel)
        self.git_margin.bind("<MouseWheel>", self._on_canvas_mousewheel)

        self.popup = None # Widget de sugestões

        # Configura as tags de sintaxe inicialmente
        if self.ctx.py_plugin:
            self.ctx.py_plugin.setup_tags(self)

    def apply_theme(self):
        theme = AppContext().theme.get("editor", {})
        self.textbox.configure(
            fg_color=theme.get("bg", "#1e1e1e"),
            text_color=theme.get("fg", "#d4d4d4")
        )
        self.textbox._textbox.configure(
            insertbackground=theme.get("cursor", "white"),
            selectbackground=theme.get("selection_bg", "#264f78")
        )
        self.line_numbers.configure(bg=theme.get("gutter_bg", "#1e1e1e"))
        self.git_margin.configure(bg=theme.get("gutter_bg", "#1e1e1e"))
        self.redraw_line_numbers()

    # --- Implementação do Protocolo TextEditor ---

    def insert(self, text: str, index: str = "insert") -> None:
        self.textbox.insert(index, text)

    def delete(self, start: str, end: Optional[str] = None) -> None:
        self.textbox.delete(start, end or f"{start} + 1 chars")

    def get_text(self, start: str = "1.0", end: str = "end") -> str:
        content = self.textbox.get(start, end)
        if end == "end" and content.endswith('\n'):
            return content[:-1]
        return content

    def set_text(self, text: str) -> None:
        self.textbox.delete("1.0", tk.END)
        self.insert(text, "1.0")
        self._after_content_load(text)

    def get_cursor_index(self) -> str:
        return self.textbox.index(tk.INSERT)

    def set_cursor(self, index: str) -> None:
        self.textbox.mark_set(tk.INSERT, index)

    def get_selection_range(self) -> Optional[tuple[str, str]]:
        try:
            if self.textbox._textbox.tag_ranges(tk.SEL):
                return (self.textbox.index(tk.SEL_FIRST), self.textbox.index(tk.SEL_LAST))
        except tk.TclError:
            pass
        return None

    def bind_key(self, key: str, callback: tk.Callable) -> None:
        def wrapper(event):
            editor_event = EditorEvent(char=event.char, keysym=event.keysym)
            return callback(editor_event)
        return self.textbox._textbox.bind(key, wrapper, add="+")

    def index_offset(self, index: str, chars: int) -> str:
        op = "+" if chars >= 0 else "-"
        return self.textbox.index(f"{index} {op} {abs(chars)} chars")

    def get_char_at(self, index: str) -> str:
        return self.textbox.get(index, f"{index} + 1 chars")

    def get_line_count(self) -> int:
        return int(self.textbox.index('end-1c').split('.')[0])

    def apply_tag(self, tag_name: str, start: str, end: str) -> None:
        self.textbox._textbox.tag_add(tag_name, start, end)

    def configure_tag(self, tag_name: str, **kwargs) -> None:
        self.textbox._textbox.tag_configure(tag_name, **kwargs)

    def get_tags(self) -> tuple[str, ...]:
        return self.textbox._textbox.tag_names()

    def delete_tag(self, tag_name: str) -> None:
        self.textbox._textbox.tag_delete(tag_name)

    def remove_tag(self, tag_name: str, start: str, end: str) -> None:
        self.textbox._textbox.tag_remove(tag_name, start, end)

    def undo(self) -> None:
        try: self.textbox._textbox.edit_undo()
        except tk.TclError: pass

    def redo(self) -> None:
        try: self.textbox._textbox.edit_redo()
        except tk.TclError: pass

    def edit_separator(self) -> None:
        try: self.textbox._textbox.edit_separator()
        except tk.TclError: pass

    def reset_undo_stack(self) -> None:
        self.textbox._textbox.edit_reset()

    def begin_undo_group(self) -> None:
        """Inicia um bloco atômico desabilitando temporariamente a pilha."""
        self.textbox._textbox.configure(autoseparators=False)

    def end_undo_group(self) -> None:
        """Fecha o bloco atômico e força um separador."""
        self.edit_separator()

    def is_in_transaction(self) -> bool:
        return AppContext()._transaction_level > 0

    # --- Métodos de UI e Eventos ---

    def _set_dirty(self, event=None):
        # Delega ao core a decisão de como tratar essa entrada de texto
        char = event.char if event else None
        AppContext().handle_typing(char)

    def _on_text_scroll(self, *args):
        """Callback for the textbox's yscrollcommand."""
        # The *args are typically (fraction_start, fraction_end) for an external scrollbar.
        self.redraw_line_numbers()
        self._update_status_bar()

    def _on_event(self, event=None):
        self.redraw_line_numbers()
        self._update_status_bar()
        
        # Dispara realce de sintaxe Python
        if AppContext().py_plugin:
            AppContext().py_plugin.highlight()
            self._trigger_autocomplete(event)
            
        # Executa plugins externos de forma desacoplada
        for plugin in getattr(AppContext(), 'external_plugins', []):
            if hasattr(plugin, 'run'):
                plugin.run()

    def _force_autocomplete(self, event=None):
        self._trigger_autocomplete(event, forced=True)
        return "break"

    def _select_all(self, event=None):
        """Seleciona todo o texto do editor."""
        self.textbox._textbox.tag_add(tk.SEL, "1.0", tk.END)
        self.textbox._textbox.mark_set(tk.INSERT, tk.END)
        self.textbox._textbox.see(tk.INSERT)
        return "break"

    def _on_key_press(self, event):
        """Intervém nas teclas de navegação quando o popup está ativo."""
        if not self.popup: return

        if event.keysym in ("Down", "n", "Next"):
            current = self.popup.curselection()
            idx = (current[0] + 1) if current else 0
            if idx < self.popup.size():
                self.popup.selection_clear(0, tk.END)
                self.popup.selection_set(idx)
                self.popup.see(idx)
            return "break"

        elif event.keysym in ("Up", "p", "Prior"):
            current = self.popup.curselection()
            idx = (current[0] - 1) if current else 0
            if idx >= 0:
                self.popup.selection_clear(0, tk.END)
                self.popup.selection_set(idx)
                self.popup.see(idx)
            return "break"

        elif event.keysym in ("Tab", "Return", "KP_Enter"):
            self._on_suggestion_select(None)
            return "break"

        elif event.keysym == "Escape":
            self._hide_autocomplete()
            return "break"

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

    def _trigger_autocomplete(self, event=None, forced=False):
        """Consulta o core e decide se mostra o popup."""
        if not event and not forced: return
        
        if not forced:
            is_char = len(event.char) > 0 and (event.char.isalnum() or event.char == ".")
            is_backspace = event.keysym == "BackSpace"
            if not (is_char or is_backspace): return

        ctx = AppContext()
        index = self.textbox.index(tk.INSERT)
        line, col = map(int, index.split("."))
        
        def on_data_ready(suggestions):
            # Volta para a thread principal do Tkinter para desenhar a UI
            self.textbox.after(0, lambda: self._update_popup_safe(suggestions))

        ctx.autocomplete_engine.request_completion(line, col, on_data_ready)

    def _update_popup_safe(self, suggestions):
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
        self.popup.selection_set(0) # Pré-seleciona a primeira opção
        
        # Posiciona o popup logo abaixo do cursor
        self.popup.place(x=root_x - self.winfo_rootx(), y=root_y - self.winfo_rooty())
        self.popup.bind("<Button-1>", self._on_suggestion_select)

    def _hide_autocomplete(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _on_suggestion_select(self, event):
        if not self.popup: return
        sel = self.popup.curselection()
        if not sel: return
        selection = self.popup.get(sel[0])
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
        if self.ctx.status_bar and self.ctx.editor:
            index = self.ctx.editor.get_cursor_index()
            line, col = index.split(".")
            self.ctx.status_bar.update_status(int(line), int(col), self.ctx.current_file or "Novo Arquivo")

    def _after_content_load(self, text: str):
        """Lógica interna de UI após carregar texto."""
        # Re-configura tags caso o tema tenha mudado ou o editor resetado
        if self.ctx.py_plugin:
            self.ctx.py_plugin.setup_tags(self)
            
        if self.ctx.autocomplete_engine and self.ctx.current_file:
            self.ctx.autocomplete_engine.notify_open(self.ctx.current_file, text)
        self.redraw_line_numbers()
        self.ctx.is_dirty = False
        
        # Atualizar visibilidade do botão Markdown
        if self.ctx.md_plugin:
            self.ctx.md_plugin.update_button_visibility(self.ctx.current_file)