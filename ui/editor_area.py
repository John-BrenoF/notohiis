#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import customtkinter as ctk
import tkinter as tk
from typing import Optional
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
        self.textbox._textbox.bind("<Control-f>", self._toggle_search)
        self.textbox._textbox.bind("<Control-F>", self._toggle_search)
        self.textbox._textbox.bind("<Configure>", self._on_event)
        self.textbox._textbox.bind("<Key>", self._set_dirty)
        
        # Navegação rápida: Alt + Seta + Número
        self.textbox._textbox.bind("<Alt-Up>", self._start_navigation_up)
        self.textbox._textbox.bind("<Alt-Down>", self._start_navigation_down)
        self.textbox._textbox.bind("<KeyPress-1>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-2>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-3>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-4>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-5>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-6>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-7>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-8>", self._on_number_input)
        self.textbox._textbox.bind("<KeyPress-9>", self._on_number_input)
        self.textbox._textbox.bind("<Escape>", self._cancel_navigation)

        self.line_numbers.bind("<MouseWheel>", self._on_canvas_mousewheel)
        self.git_margin.bind("<MouseWheel>", self._on_canvas_mousewheel)

        self.popup = None # Widget de sugestões

        # Estado para navegação rápida (Alt + Seta + Número)
        self.navigation_mode = None  # "up" ou "down" ou None
        self.navigation_timer = None

        # Estado da busca
        self.search_matches = []
        self.current_match_index = -1
        self._config_search_tags()

        # Configura as tags de sintaxe inicialmente
        if self.ctx.py_plugin:
            self.ctx.py_plugin.setup_tags(self)

    def _config_search_tags(self):
        """Configura as cores das tags de highlight de busca."""
        self.textbox._textbox.tag_configure("search_match", background="#4a4a4a", foreground="#ffffff")
        self.textbox._textbox.tag_configure("search_active", background="#d7ba7d", foreground="#000000")

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
        self._config_search_tags()

    # --- Implementação da Busca (Ctrl+F) ---

    def _toggle_search(self, event=None):
        if hasattr(self.ctx, 'search_bar') and self.ctx.search_bar:
            if self.ctx.search_bar.winfo_ismapped():
                self.ctx.search_bar.hide()
            else:
                self.ctx.search_bar.show()
        return "break"

    def clear_search_highlight(self):
        """Limpa as marcações de busca do editor."""
        self.textbox._textbox.tag_remove("search_match", "1.0", tk.END)
        self.textbox._textbox.tag_remove("search_active", "1.0", tk.END)
        self.search_matches = []
        self.current_match_index = -1

    def highlight_search(self, term: str, match_case: bool = False):
        """Busca o termo, aplica highlight e retorna a tupla (atual, total)."""
        self.clear_search_highlight()
        if not term:
            return 0, 0

        start_pos = "1.0"
        nocase = not match_case
        
        while True:
            start_pos = self.textbox._textbox.search(term, start_pos, stopindex=tk.END, nocase=nocase)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(term)}c"
            self.textbox._textbox.tag_add("search_match", start_pos, end_pos)
            self.search_matches.append((start_pos, end_pos))
            start_pos = end_pos
        
        if self.search_matches:
            return self.goto_next_match(0) # Foca na primeira ocorrência sem pular
            
        return 0, 0

    def goto_next_match(self, step=1):
        """Navega entre os resultados da busca e retorna a tupla (atual, total)."""
        if not self.search_matches:
            return 0, 0
        
        self.textbox._textbox.tag_remove("search_active", "1.0", tk.END)
        self.current_match_index = (self.current_match_index + step) % len(self.search_matches)
        
        start_pos, end_pos = self.search_matches[self.current_match_index]
        self.textbox._textbox.tag_add("search_active", start_pos, end_pos)
        self.textbox._textbox.see(start_pos)
        self.set_cursor(start_pos)
        
        return self.current_match_index + 1, len(self.search_matches)

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

        # Se houver um gerenciador de abas ativo, sincroniza o conteúdo atual
        if getattr(AppContext(), 'tab_bridge', None):
            AppContext().tab_bridge.update_active_tab_content(self.get_text())

    def _force_autocomplete(self, event=None):
        self._trigger_autocomplete(event, forced=True)
        return "break"

    def _select_all(self, event=None):
        """Seleciona todo o texto do editor."""
        self.textbox._textbox.tag_add(tk.SEL, "1.0", tk.END)
        self.textbox._textbox.mark_set(tk.INSERT, tk.END)
        self.textbox._textbox.see(tk.INSERT)
        return "break"

    # --- Navegação Rápida (Alt + Seta + Número) ---

    def _start_navigation_up(self, event=None):
        """Inicia modo de navegação para cima."""
        self.navigation_mode = "up"
        self._schedule_navigation_timeout()
        return "break"

    def _start_navigation_down(self, event=None):
        """Inicia modo de navegação para baixo."""
        self.navigation_mode = "down"
        self._schedule_navigation_timeout()
        return "break"

    def _on_number_input(self, event=None):
        """Processa entrada de número quando em modo navegação."""
        if self.navigation_mode and event and event.char.isdigit():
            lines_count = int(event.char)
            self.move_cursor_by_lines(lines_count, self.navigation_mode)
            self.navigation_mode = None
            if self.navigation_timer:
                self.after_cancel(self.navigation_timer)
                self.navigation_timer = None
            return "break"
        return None

    def _cancel_navigation(self, event=None):
        """Cancela modo de navegação se ativo."""
        if self.navigation_mode:
            self.navigation_mode = None
            if self.navigation_timer:
                self.after_cancel(self.navigation_timer)
                self.navigation_timer = None
            return "break"

    def _schedule_navigation_timeout(self):
        """Agenda timeout para cancelar navegação se não houver número."""
        if self.navigation_timer:
            self.after_cancel(self.navigation_timer)
        self.navigation_timer = self.after(1000, self._cancel_navigation)

    def move_cursor_by_lines(self, lines: int, direction: str) -> None:
        """
        Move o cursor N linhas para cima ou para baixo.
        """
        try:
            current_index = self.textbox.index(tk.INSERT)
            current_line = int(current_index.split('.')[0])
            
            if direction == "up":
                new_line = max(1, current_line - lines)
            else:  # down
                total_lines = self.get_line_count()
                new_line = min(total_lines, current_line + lines)
            
            self.set_cursor(f"{new_line}.0")
            self.textbox.see(tk.INSERT)
        except (ValueError, tk.TclError):
            pass

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
        i = self.textbox.index("@0,0") 
        while True:
            dline = self.textbox._textbox.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            color = AppContext().theme.get("editor", {}).get("gutter_fg", "#858585")
            self.line_numbers.create_text(40, y, anchor="ne", text=linenum, fill=color, font=("Consolas", 11))
            i = self.textbox.index(f"{i}+1line") 

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
            self.textbox.after(0, lambda: self._update_popup_safe(suggestions))

        ctx.autocomplete_engine.request_completion(line, col, on_data_ready)

    def _update_popup_safe(self, suggestions):
        if suggestions:
            self._show_autocomplete_popup(suggestions)
        else:
            self._hide_autocomplete()

    def _show_autocomplete_popup(self, suggestions):
        self._hide_autocomplete()
        
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
        self.popup.selection_set(0) 
        
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
        self.textbox._textbox.delete("insert wordstart", tk.INSERT)
        self.textbox.insert(tk.INSERT, selection)
        self._hide_autocomplete()

    def _on_canvas_mousewheel(self, event):
        if event.num == 4 or event.delta > 0: 
            self.textbox._textbox.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0: 
            self.textbox._textbox.yview_scroll(1, "units")
        return "break" 

    def _update_status_bar(self):
        if self.ctx.status_bar and self.ctx.editor:
            index = self.ctx.editor.get_cursor_index()
            line, col = index.split(".")
            self.ctx.status_bar.update_status(int(line), int(col), self.ctx.current_file or "Novo Arquivo")

    def _after_content_load(self, text: str):
        if self.ctx.py_plugin:
            self.ctx.py_plugin.setup_tags(self)
            
        if self.ctx.autocomplete_engine and self.ctx.current_file:
            self.ctx.autocomplete_engine.notify_open(self.ctx.current_file, text)
        self.redraw_line_numbers()
        self.ctx.is_dirty = False
        
        if self.ctx.md_plugin:
            self.ctx.md_plugin.update_button_visibility(self.ctx.current_file)