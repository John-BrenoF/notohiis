import customtkinter as ctk
import tkinter as tk
import os
from core.src.file_manager import FileManager
from core.src.app_context import AppContext
from core.src.buffer import BufferManager
from tkinter import messagebox, simpledialog

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
        
        self.label = ctk.CTkLabel(self, text="EXPLORER", font=("Segoe UI", 12, "bold"))
        self.label.pack(pady=10, padx=10, fill="x")
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.scrollable_frame.pack(fill="both", expand=True)
        
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)
        self.context_menu.add_command(label="Novo Arquivo", command=self._menu_new_file)
        self.context_menu.add_command(label="Nova Pasta", command=self._menu_new_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Excluir", command=self._menu_delete)

        self.bind("<Button-3>", self._show_context_menu)
        self.refresh_explorer()

    def refresh_explorer(self):
        """Popula a lista de arquivos do diretório atual."""
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

    def _add_item(self, name, path, is_dir):
        prefix = "📁 " if is_dir else "📄 "
        btn = ctk.CTkButton(
            self.scrollable_frame, 
            text=f"{prefix}{name}",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: self._handle_click(path, is_dir)
        )
        btn.pack(fill="x", padx=5, pady=2)
        btn.bind("<Button-3>", lambda e: self._show_context_menu(e, path))

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

    def _show_context_menu(self, event, target_path=None):
        self._menu_target = target_path or AppContext().project_root
        self.context_menu.post(event.x_root, event.y_root)

    def _menu_new_file(self):
        name = simpledialog.askstring("Novo Arquivo", "Nome do arquivo:")
        if name and self._menu_target:
            base = self._menu_target if os.path.isdir(self._menu_target) else os.path.dirname(self._menu_target)
            FileManager.create_file(os.path.join(base, name))
            self.refresh_explorer()

    def _menu_new_folder(self):
        name = simpledialog.askstring("Nova Pasta", "Nome da pasta:")
        if name and self._menu_target:
            base = self._menu_target if os.path.isdir(self._menu_target) else os.path.dirname(self._menu_target)
            FileManager.create_directory(os.path.join(base, name))
            self.refresh_explorer()

    def _menu_delete(self):
        if self._menu_target and messagebox.askyesno("Excluir", f"Deseja excluir {os.path.basename(self._menu_target)}?"):
            FileManager.delete_path(self._menu_target)
            self.refresh_explorer()