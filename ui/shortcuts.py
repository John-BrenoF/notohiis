from core.src.app_context import AppContext

class ShortcutManager:
    """Gerencia os atalhos de teclado da aplicação."""
    
    @staticmethod
    def setup_shortcuts(window):
        window.bind("<Control-b>", ShortcutManager.toggle_sidebar)
        window.bind("<Control-B>", ShortcutManager.toggle_sidebar)

    @staticmethod
    def toggle_sidebar(event=None):
        ctx = AppContext()
        if ctx.sidebar:
            # Se a largura for 0 ou próxima, expande; caso contrário, recolhe.
            if ctx.sidebar.winfo_width() <= 1:
                ctx.sidebar.configure(width=200)
            else:
                ctx.sidebar.configure(width=0)