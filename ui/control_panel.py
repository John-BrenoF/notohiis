import customtkinter as ctk
import os
import tkinter as tk
from core.src.app_context import AppContext
from core.src.buffer import BufferManager

class ControlPanel(ctk.CTkToplevel):
    """Painel central de controle para configurações e plugins."""
    def __init__(self, master):
        super().__init__(master)
        self.title("Notohiis Control Panel")
        self.geometry("720x520")
        self.attributes("-topmost", True)
        self.grab_set() # Torna o diálogo modal
        
        self.ctx = AppContext()
        self._center_window(720, 520)
        
        # Configuração de Cores do Painel
        self.bg_card = "#1e1e20"
        self.configure(fg_color="#141417")
        
        # Layout Principal (2 Colunas)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Coluna 1: Configurações ---
        self.config_frame = ctk.CTkFrame(self, fg_color=self.bg_card, corner_radius=15, border_width=2, border_color="#333335")
        self.config_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Título com padding superior aumentado para compensar a falta do ícone
        ctk.CTkLabel(self.config_frame, text="Configurações", font=("Segoe UI", 20, "bold")).pack(pady=(50, 5))
        
        desc_cfg = "Personalize o tema,\nfontes e cores do editor."
        ctk.CTkLabel(self.config_frame, text=desc_cfg, font=("Segoe UI", 13), text_color="#9da5b4").pack(pady=10)

        # Caminho para o arquivo de tema
        theme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estilo", "editor.json")
        
        self.btn_edit = ctk.CTkButton(
            self.config_frame, 
            text="Abrir editor.json",
            font=("Segoe UI", 12, "bold"),
            height=35,
            command=lambda: self._open_config(theme_path)
        )
        self.btn_edit.pack(pady=40, padx=40, fill="x", side="bottom")

        # --- Coluna 2: Plugins ---
        self.plugins_frame = ctk.CTkFrame(self, fg_color=self.bg_card, corner_radius=15, border_width=2, border_color="#333335")
        self.plugins_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.plugins_frame, text="Plugins Ativos", font=("Segoe UI", 20, "bold")).pack(pady=(50, 5))

        # Container com scroll para listar os plugins
        self.scroll_plugins = ctk.CTkScrollableFrame(
            self.plugins_frame, 
            fg_color="#121214", 
            scrollbar_button_color="#333335",
            corner_radius=8
        )
        self.scroll_plugins.pack(fill="both", expand=True, pady=20, padx=20)
        
        self._load_plugins()

        # Rodapé com instrução
        ctk.CTkLabel(self, text="Pressione [ESC] para fechar", font=("Segoe UI", 10), text_color="gray").grid(row=1, column=0, columnspan=2, pady=10)

        # Botão de Fechar (Esc)
        self.bind("<Escape>", lambda e: self.destroy())

    def _center_window(self, width, height):
        self.update_idletasks()
        from ui.shortcuts import ShortcutManager
        ShortcutManager._center_window(self, width, height)

    def _open_config(self, path):
        """Abre o arquivo de tema no editor para edição direta."""
        if os.path.exists(path):
            content = BufferManager.read_file(path)
            # Garante que o buffer seja limpo para a nova sessão de edição
            if self.ctx.editor:
                self.ctx.editor.set_text(content)
            self.ctx.current_file = path
            self.ctx.is_dirty = False
            if self.ctx.status_bar:
                # Força a atualização visual para mostrar que estamos no editor.json
                self.ctx.status_bar.update_status(1, 0, "CONFIG: editor.json")
            self.destroy()

    def _load_plugins(self):
        """Escaneia diretórios de plugins e lista no painel."""
        # Caminho base do projeto para localizar core_plugin e plugins
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = {
            "Core": os.path.join(base_dir, "core", "core_plugin"),
            "User": os.path.join(base_dir, "plugins")
        }

        found = False
        for label, p in paths.items():
            if os.path.exists(p):
                for item in sorted(os.listdir(p)):
                    if item.startswith("__") or item == "init.py": continue
                    found = True
                    # Ícone de tomada para todos os plugins
                    icon = "󰚥"
                    name = item.replace(".py", "")
                    
                    # Criando um mini-card para cada plugin para melhorar o UX
                    item_frame = ctk.CTkFrame(
                        self.scroll_plugins, 
                        fg_color="transparent", 
                        height=35
                    )
                    item_frame.pack(fill="x", padx=2, pady=2)

                    # Label do ícone
                    ctk.CTkLabel(
                        item_frame, 
                        text=icon, 
                        font=("Segoe UI Symbol", 14),
                        text_color="#61afef" if "Core" in label else "#98c379",
                        width=30
                    ).pack(side="left", padx=(5, 5))

                    # Label do nome
                    ctk.CTkLabel(
                        item_frame, 
                        text=name, 
                        font=("Segoe UI", 12),
                        text_color="#abb2bf"
                    ).pack(side="left")
        
        if not found:
            ctk.CTkLabel(self.scroll_plugins, text="Nenhum plugin detectado", font=("Segoe UI", 10), text_color="gray").pack(pady=20)