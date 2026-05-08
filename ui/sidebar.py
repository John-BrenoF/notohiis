import customtkinter as ctk
import tkinter as tk
import os
from core.src.file_manager import FileManager
from core.src.app_context import AppContext
from core.src.buffer import BufferManager
from tkinter import messagebox

class Sidebar(ctk.CTkFrame):
    """Explorador de arquivos lateral."""
    def __init__(self, master, width=0, corner_radius=0, **kwargs):
        # Extraímos width e corner_radius da assinatura para evitar duplicidade no **kwargs
        super().__init__(
            master, 
            width=width, 
            corner_radius=corner_radius, 
            **kwargs
        )
        self.grid_propagate(False)
        self.item_widgets = {}  # Mapeia caminhos para seus widgets na UI
        theme = AppContext().theme.get("sidebar", {})
        self.configure(fg_color=theme.get("bg", "#1a1a1c"))
        
        # Cabeçalho da Sidebar
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(15, 5), padx=10)
        
        self.label = ctk.CTkLabel(self.header_frame, text="EXPLORER", font=("Segoe UI", 11, "bold"), text_color=theme.get("label", "gray"))
        self.label.pack(side="left")

        # Botões de ação rápida (estilo VS Code)
        self.refresh_btn = ctk.CTkButton(
            self.header_frame, text="󰑐", width=20, height=20, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), command=self.refresh_explorer
        )
        self.refresh_btn.pack(side="right")

        self.new_folder_btn = ctk.CTkButton(
            self.header_frame, text="󰉋", width=20, height=20, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), command=lambda: self._show_inline_entry(is_dir=True)
        )
        self.new_folder_btn.pack(side="right", padx=2)

        self.new_file_btn = ctk.CTkButton(
            self.header_frame, text="󰈔", width=20, height=20, corner_radius=4,
            fg_color="transparent", hover_color=theme.get("hover", "#2d2d2d"),
            text_color=theme.get("label", "gray"), command=lambda: self._show_inline_entry(is_dir=False)
        )
        self.new_file_btn.pack(side="right", padx=2)
        
        # Configuração minimalista da área de scroll
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, 
            corner_radius=0, 
            fg_color="transparent",
            scrollbar_button_color=theme.get("hover", "#2c313a"),
            scrollbar_button_hover_color=theme.get("label", "#5c6370")
        )
        self.scrollable_frame.pack(fill="both", expand=True)
        
        # Ajuste técnico para tornar a barra de scroll mais fina (minimalista)
        self.scrollable_frame._scrollbar.configure(width=8)

        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)
        self.context_menu.add_command(label="Novo Arquivo", command=self._menu_new_file)
        self.context_menu.add_command(label="Nova Pasta", command=self._menu_new_folder)
        self.context_menu.add_command(label="Renomear", command=self._menu_rename)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Excluir", command=self._menu_delete)

        self.bind("<Button-3>", self._show_context_menu)
        self.refresh_explorer()

    def refresh_explorer(self):
        """Popula a lista de arquivos do diretório atual."""
        self.item_widgets.clear()
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        ctx = AppContext()
        if not ctx.project_root:
            ctk.CTkLabel(self.scrollable_frame, text="Nenhum diretório\naberto", text_color="gray").pack(pady=20)
            return

        items = FileManager.list_directory(ctx.project_root)
        
        # Botão para voltar (opcional)
        if ctx.project_root != "/":
            self._add_item("..", os.path.dirname(ctx.project_root), True)

        for item in items:
            self._add_item(item["name"], item["path"], item["is_dir"])

    def _get_icon(self, name, is_dir):
        """Retorna o ícone baseado na extensão ou tipo."""
        if is_dir:
            return "󰉋 "
        
        ext = os.path.splitext(name)[1].lower()
        icons = {
            '.py': ' ',
            '.md': '󰍔 ',
            '.json': ' ',
            '.txt': '󰈙 ',
            '.sh': '󱆃 ',
            '.gitignore': '󰊢 ',
            '.session_config': '󰒓 ',
            '.html': ' ',
            '.css': ' ',
            '.js': ' '
        }
        return icons.get(ext, "󰈔 ")

    def _add_item(self, name, path, is_dir):
        icon = self._get_icon(name, is_dir)
        theme = AppContext().theme.get("sidebar", {})
        btn = ctk.CTkButton(
            self.scrollable_frame, 
            text=f"{icon}    {name}",
            anchor="w",
            fg_color="transparent",
            text_color=theme.get("fg", "#cccccc"),
            hover_color=theme.get("hover", "#2d2d2d"),
            font=("Segoe UI", 12),
            height=28,
            command=lambda: self._handle_click(path, is_dir)
        )
        btn.pack(fill="x", padx=5, pady=2)
        self.item_widgets[path] = btn
        btn.bind("<Button-3>", lambda e: self._show_context_menu(e, path))
        
        # Vincula o scroll em cada botão item
        self._bind_scroll_to_widget(btn)

    def _bind_scroll_to_widget(self, widget):
        """Aplica os binds de scroll de forma universal ao widget."""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Motor de scroll manual e resiliente para suportar Linux/Win/Mac."""
        # 1. Tenta usar o método interno do CustomTkinter (mais seguro)
        if hasattr(self.scrollable_frame, "_on_mousewheel"):
            self.scrollable_frame._on_mousewheel(event)
            return "break"

        # 2. Fallback manual acessando o canvas de scroll real (_parent_canvas)
        # Evitamos winfo_children pois botões internos têm 'canvas' no nome do widget
        canvas = getattr(self.scrollable_frame, "_parent_canvas", None)
        if canvas and hasattr(canvas, "yview_scroll"):
            # No Linux usa event.num, no Win/Mac usa event.delta
            direction = -1 if (event.num == 4 or event.delta > 0) else 1
            canvas.yview_scroll(direction, "units")
            
        return "break"

    def _handle_click(self, path, is_dir):
        ctx = AppContext()
        if is_dir:
            ctx.project_root = path
            self.refresh_explorer()
        else:
            content = BufferManager.read_file(path)
            ctx.editor_container.set_text(content)
            ctx.current_file = path
            ctx.is_dirty = False
            ctx.status_bar.update_status(1, 0, path)
            
            # Dispara realce de sintaxe imediatamente após carregar o arquivo
            if ctx.py_plugin:
                ctx.py_plugin.highlight()

    def _show_inline_entry(self, is_dir=False, target_path=None):
        """Cria um campo de texto temporário na lista para nomear novo item."""
        ctx = AppContext()
        if not ctx.project_root: return

        # Define o widget de referência para posicionamento
        anchor_widget = self.item_widgets.get(target_path) if target_path else None

        inline_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#2c313a", height=30, corner_radius=4)
        
        # Se houver um âncora (via menu de contexto), coloca depois dele. Senão, no topo.
        if anchor_widget:
            inline_frame.pack(fill="x", padx=5, pady=2, after=anchor_widget)
        else:
            children = self.scrollable_frame.winfo_children()
            inline_frame.pack(fill="x", padx=5, pady=2, before=children[0] if children else None)

        icon = "󰉋 " if is_dir else "󰈔 "
        icon_label = ctk.CTkLabel(inline_frame, text=icon, font=("Segoe UI", 12))
        icon_label.pack(side="left", padx=(5, 10))
        
        entry = ctk.CTkEntry(
            inline_frame, 
            height=24, 
            font=("Segoe UI", 11), 
            border_width=0,
            fg_color="#1d2026"
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry.focus_set()

        # Garante que o scroll funcione mesmo com a caixa de texto aberta
        self._bind_scroll_to_widget(inline_frame)
        self._bind_scroll_to_widget(icon_label)
        self._bind_scroll_to_widget(entry)

        def confirm(event=None):
            name = entry.get()
            if name:
                # Se o target_path for um arquivo, usamos o diretório dele
                base_dir = ctx.project_root
                if target_path:
                    base_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
                
                new_path = os.path.join(base_dir, name)
                if is_dir: FileManager.create_directory(new_path)
                else: FileManager.create_file(new_path)
                self.refresh_explorer()
            inline_frame.destroy()

        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", lambda e: inline_frame.destroy())
        entry.bind("<FocusOut>", lambda e: inline_frame.destroy())

    def _show_context_menu(self, event, target_path=None):
        self._menu_target = target_path or AppContext().project_root
        self.context_menu.post(event.x_root, event.y_root)

    def _menu_new_file(self):
        """Aciona a criação inline via menu de contexto."""
        self._show_inline_entry(is_dir=False, target_path=self._menu_target)

    def _menu_new_folder(self):
        """Aciona a criação inline via menu de contexto."""
        self._show_inline_entry(is_dir=True, target_path=self._menu_target)

    def _menu_rename(self):
        from tkinter import simpledialog
        if not self._menu_target: return
        old_name = os.path.basename(self._menu_target)
        new_name = simpledialog.askstring("Renomear", "Novo nome:", initialvalue=old_name)
        if new_name and new_name != old_name:
            if FileManager.rename_path(self._menu_target, new_name):
                self.refresh_explorer()
            else:
                messagebox.showerror("Erro", "Não foi possível renomear o item.", parent=self)

    def _menu_delete(self):
        if self._menu_target and messagebox.askyesno("Excluir", f"Deseja excluir {os.path.basename(self._menu_target)}?"):
            if FileManager.delete_path(self._menu_target):
                self.refresh_explorer()
            else:
                messagebox.showerror("Erro", "Não foi possível excluir o item.", parent=self)