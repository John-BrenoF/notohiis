import customtkinter as ctk

class StatusBar(ctk.CTkFrame):
    """Barra inferior para exibição de métricas."""
    def __init__(self, master, **kwargs):
        super().__init__(master, height=25, corner_radius=0, **kwargs)
        
        self.info_label = ctk.CTkLabel(
            self, 
            text="Linha: 1, Coluna: 0 | UTF-8", 
            font=("Consolas", 12)
        )
        self.info_label.pack(side="right", padx=20)
        
        self.file_label = ctk.CTkLabel(
            self, 
            text="Novo Arquivo", 
            font=("Consolas", 12)
        )
        self.file_label.pack(side="left", padx=20)

    def update_status(self, line: int, column: int, file_path: str = "Novo Arquivo"):
        self.info_label.configure(text=f"Linha: {line}, Coluna: {column} | UTF-8")
        self.file_label.configure(text=file_path)