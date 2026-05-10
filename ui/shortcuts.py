import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
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
        window.bind("<F1>", ShortcutManager.show_help)
        window.bind("<Control-n>", ShortcutManager.new_buffer)
        window.bind("<Control-n>", ShortcutManager.new_buffer)
        window.bind("<Control-r>", ShortcutManager.open_quick_access)
        window.bind("<Control-R>", ShortcutManager.open_quick_access)
        
        # Painel de Controle (Configurações e Plugins)
        window.bind("<Control-Alt-c>", ShortcutManager.open_control_panel)
        window.bind("<Control-Alt-C>", ShortcutManager.open_control_panel)
        
        # Atalhos de Plugins
        window.bind("<Control-m>", lambda e: AppContext().md_plugin.toggle_preview() if AppContext().md_plugin else None)
        window.bind("<Control-M>", lambda e: AppContext().md_plugin.toggle_preview() if AppContext().md_plugin else None)
        window.bind("<Control-g>", lambda e: AppContext().git_plugin.quick_commit_ui() if AppContext().git_plugin else None)
        window.bind("<Control-G>", lambda e: AppContext().git_plugin.quick_commit_ui() if AppContext().git_plugin else None)

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
    def _center_window(window, width, height):
        window.update_idletasks()
        
        # Define como transiente e não redimensionável para que o compositor Wayland (Niri/Hyprland)
        # entenda que é um diálogo e aplique as regras de flutuação e centralização.
        master = AppContext().window
        if master:
            window.transient(master)
        window.resizable(False, False)

        # Para centralizar no meio da tela em Wayland (KDE, Gnome, Niri, Hyprland)
        # usamos as dimensões da tela (screen) em vez das coordenadas da janela mestre.
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max(0, (screen_width // 2) - (width // 2))
        y = max(0, (screen_height // 2) - (height // 2))
        window.geometry(f"{width}x{height}+{x}+{y}")

    @staticmethod
    def save_file(event=None):
        ctx = AppContext()
        if not ctx.current_file:
            path = filedialog.asksaveasfilename(defaultextension=".txt")
            if not path: return
            ctx.current_file = path

        if ctx.editor:
            content = ctx.editor.get_text()
            if BufferManager.save_file(ctx.current_file, content):
                ctx.is_dirty = False
                if ctx.sidebar: ctx.sidebar.refresh_explorer()
                # O próprio editor costuma atualizar o status via eventos de teclado, 
                # mas forçamos aqui para garantir sincronia após o save.
                if hasattr(ctx.editor, '_update_status_bar'):
                    ctx.editor._update_status_bar()

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

        def proceed():
            ctx.current_file = None
            ctx.is_dirty = False
            if ctx.editor:
                ctx.editor.set_text("")
            if ctx.status_bar:
                ctx.status_bar.update_status(1, 0, "Novo Arquivo")

        if ctx.is_dirty:
            dialog = ctk.CTkToplevel(ctx.window)
            dialog.title("Descartar Alterações")
            dialog.attributes("-topmost", True)
            ShortcutManager._center_window(dialog, 350, 150)
            
            ctk.CTkLabel(dialog, text="Alterações não salvas serão perdidas.\nContinuar?", pady=20).pack()
            
            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            ctk.CTkButton(btn_frame, text="Sim", width=100, command=lambda: [dialog.destroy(), proceed()]).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Não", width=100, fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)
            return "break"
            
        proceed()
        return "break"

    @staticmethod
    def show_help(event=None):
        ctx = AppContext()
        help_window = ctk.CTkToplevel(ctx.window)
        help_window.title("Ajuda - Notohiis")
        help_window.attributes("-topmost", True)
        ShortcutManager._center_window(help_window, 400, 350)

        ctk.CTkLabel(help_window, text="Atalhos do Notohiis", font=("Segoe UI", 18, "bold"), pady=20).pack()

        shortcuts_frame = ctk.CTkFrame(help_window, fg_color="transparent")
        shortcuts_frame.pack(fill="both", expand=True, padx=40)

        shortcuts = [
            ("Ctrl+N", "Novo Arquivo"),
            ("Ctrl+S", "Salvar"),
            ("Ctrl+O", "Abrir Pasta"),
            ("Ctrl+B", "Alternar Sidebar"),
            ("Ctrl+M", "Markdown Preview"),
            ("Ctrl+G", "Git Quick Commit"),
            ("F1", "Ajuda")
        ]

        for key, desc in shortcuts:
            row = ctk.CTkFrame(shortcuts_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=key, font=("Consolas", 12, "bold"), text_color="#61afef", width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Segoe UI", 12), anchor="w").pack(side="left")

        ctk.CTkButton(help_window, text="Entendido", command=help_window.destroy).pack(pady=20)

    @staticmethod
    def open_control_panel(event=None):
        from ui.control_panel import ControlPanel
        ctx = AppContext()
        ControlPanel(ctx.window)

    @staticmethod
    def open_quick_access(event=None):
        from ui.quick_access import QuickAccess
        QuickAccess(AppContext().window)