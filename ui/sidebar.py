import customtkinter as ctk
import os
from core.src.file_manager import FileManager
from core.src.app_context import AppContext

class Sidebar(ctk.CTkFrame):
    """Explorador de arquivos lateral."""
    def __init__(self, master, **kwargs):
        super().__init__(master, width=0, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        
        self.label = ctk.CTkLabel(self, text="EXPLORER", font=("Segoe UI", 12, "bold"))
        self.label.pack(pady=10, padx=10, fill="x")
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.scrollable_frame.pack(fill="both", expand=True)
        
        self.refresh_explorer()

    def refresh_explorer(self):
        """Popula a lista de arquivos do diretório atual."""
        for child in self.scrollable_frame.winfo_children():
            child.destroy()
            
        current_dir = os.getcwd()
        items = FileManager.list_directory(current_dir)
        
        for item in items:
            prefix = "📁 " if item["is_dir"] else "📄 "
            btn = ctk.CTkButton(
                self.scrollable_frame, 
                text=f"{prefix}{item['name']}",
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30")
            )
            btn.pack(fill="x", padx=5, pady=2)