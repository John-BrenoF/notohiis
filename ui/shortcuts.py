import tkinter as tk
from tkinter import filedialog, messagebox
from core.src.app_context import AppContext
from core.src.buffer import BufferManager
from core.src.session import SessionManager

class ShortcutManager:
    """Gerencia os atalhos de teclado da aplicação."""
    
    @staticmethod
    def setup_shortcuts(window):
        window.bind("<Control-b>", ShortcutManager.toggle_sidebar)
        window.bind("<Control-B>", ShortcutManager.toggle_sidebar)
        window.bind("<Control-s>", ShortcutManager.save_file)
        window.bind("<Control-S>", ShortcutManager.save_file)
        window.bind("<Control-o>", ShortcutManager.open_folder)
        window.bind("<Control-n>", ShortcutManager.new_buffer)

    @staticmethod
    def toggle_sidebar(event=None):
        ctx = AppContext()
        if ctx.sidebar:
            if ctx.sidebar.winfo_ismapped(): # Check if it's currently visible
                ctx.sidebar.grid_forget()
                # When sidebar is hidden, the editor should take full width
                ctx.window.grid_columnconfigure(0, weight=0) # Sidebar column
                ctx.window.grid_columnconfigure(1, weight=1) # Editor column
            else:
                ctx.sidebar.grid(row=0, column=0, sticky="nsew", rowspan=2)
                # When sidebar is shown, it takes its width, editor takes rest
                ctx.window.grid_columnconfigure(0, weight=0) # Sidebar column (fixed width by widget)
                ctx.window.grid_columnconfigure(1, weight=1) # Editor column
            ctx.window.update_idletasks() # Force redraw of the main window layout
        return "break" # Stop event propagation

    @staticmethod
    def save_file(event=None):
        ctx = AppContext()
        if not ctx.current_file:
            path = filedialog.asksaveasfilename(defaultextension=".txt")
            if not path: return
            ctx.current_file = path
        
        content = ctx.editor_container.get_text().rstrip('\n') # Remove trailing newline from Tkinter Text
        if BufferManager.save_file(ctx.current_file, content):
            ctx.is_dirty = False
            ctx.editor_container._update_status_bar()
            if ctx.sidebar: ctx.sidebar.refresh_explorer()

    @staticmethod
    def open_folder(event=None):
        ctx = AppContext()
        path = filedialog.askdirectory()
        if path:
            ctx.project_root = path
            SessionManager.save_session(path)
            if ctx.sidebar:
                ctx.sidebar.refresh_explorer()
            if ctx.status_bar:
                ctx.status_bar.update_status(1, 0, f"Projeto: {path}")

    @staticmethod
    def new_buffer(event=None):
        ctx = AppContext()
        if ctx.is_dirty:
            if not messagebox.askyesno("Descartar", "Alterações não salvas serão perdidas. Continuar?"):
                return
        ctx.current_file = None
        ctx.is_dirty = False
        ctx.editor_container.set_text("")
        if ctx.status_bar:
            ctx.status_bar.update_status(1, 0, "Novo Arquivo")
        return "break"