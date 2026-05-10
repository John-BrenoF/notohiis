"""
Plugin de visualização de imagens para o editor Notohiis.
Suporta zoom, pan e ajuste automático.
Dependência: pip install Pillow
"""

import os
import tkinter as tk
from typing import Optional
import customtkinter as ctk
from PIL import Image, ImageTk
from core.src.app_context import AppContext

class ImageViewerCanvas(tk.Canvas):
    """Canvas para visualização de imagem com suporte a Zoom e Pan."""
    
    def __init__(self, master, **kwargs):
        # Usamos o fundo do tema do editor se disponível
        bg_color = kwargs.pop('bg', '#1e1e1e')
        super().__init__(master, bg=bg_color, highlightthickness=0, **kwargs)
        
        self.image_raw = None
        self.image_tk = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Bindings para Pan (Arraste)
        self.bind("<ButtonPress-1>", self._start_pan)
        self.bind("<B1-Motion>", self._execute_pan)
        
        # Bindings para Zoom (Scroll)
        self.bind("<MouseWheel>", self._on_zoom)      # Windows/macOS
        self.bind("<Button-4>", self._on_zoom)        # Linux Scroll Up
        self.bind("<Button-5>", self._on_zoom)        # Linux Scroll Down

    def load_image(self, path: str):
        """Carrega e centraliza a imagem."""
        try:
            self.image_raw = Image.open(path)
            self.scale = 1.0
            self.offset_x = 0
            self.offset_y = 0
            
            # Força o cálculo inicial de escala para caber na tela
            self.update()
            self._fit_to_screen()
            self.render()
        except Exception as e:
            print(f"[IMAGE PLUGIN] Erro ao carregar: {e}")

    def _fit_to_screen(self):
        if not self.image_raw: return
        
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        img_w, img_h = self.image_raw.size

        if canvas_w > 0 and canvas_h > 0:
            ratio = min(canvas_w / img_w, canvas_h / img_h)
            self.scale = min(ratio, 1.0) # Não amplia imagens pequenas por padrão

    def render(self):
        self.delete("all")
        if not self.image_raw: return

        w, h = self.image_raw.size
        new_size = (int(w * self.scale), int(h * self.scale))
        
        if new_size[0] <= 0 or new_size[1] <= 0: return

        # Redimensionamento de alta qualidade
        resized = self.image_raw.resize(new_size, Image.Resampling.LANCZOS)
        self.image_tk = ImageTk.PhotoImage(resized)

        # Centralização básica + offsets do Pan
        cx = (self.winfo_width() // 2) + self.offset_x
        cy = (self.winfo_height() // 2) + self.offset_y
        
        self.create_image(cx, cy, image=self.image_tk, anchor="center")

    def _start_pan(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _execute_pan(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.offset_x += dx
        self.offset_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.render()

    def _on_zoom(self, event):
        if not self.image_raw: return
        
        # Lógica para diferentes sistemas operacionais
        delta = 0
        if event.num == 4 or event.delta > 0: delta = 1
        elif event.num == 5 or event.delta < 0: delta = -1

        factor = 1.1 if delta > 0 else 0.9
        new_scale = self.scale * factor
        
        # Limites de zoom: 5% a 1000%
        if 0.05 < new_scale < 10.0:
            self.scale = new_scale
            self.render()
        return "break"

class ImagePlugin:
    """Plugin para visualização de arquivos de imagem."""
    
    EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.tiff'}

    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.canvas = None
        self.info_bar = None
        self.is_active = {} # Estado por arquivo

    def _inject_ui(self):
        """Injeta o botão na StatusBar se ainda não existir."""
        if not hasattr(self, 'btn_toggle') and self.ctx.status_bar:
            self.btn_toggle = ctk.CTkButton(
                self.ctx.status_bar,
                text="Visualizar Imagem",
                width=110, height=20,
                font=("Segoe UI", 10),
                command=self.toggle_view
            )

    def update_visibility(self):
        self._inject_ui()
        if not hasattr(self, 'btn_toggle'): return

        path = self.ctx.current_file
        is_image = path and os.path.splitext(path)[1].lower() in self.EXTENSIONS
        
        if is_image:
            self.btn_toggle.pack(side="right", padx=10)
            # Se o arquivo mudou e estava ativo, resetamos o estado
            if self.is_active.get(path):
                self.btn_toggle.configure(fg_color="#1f538d", text="Ver Texto")
            else:
                self.btn_toggle.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="Visualizar Imagem")
        else:
            self.btn_toggle.pack_forget()
            # Se o canvas de imagem estava visível, restaura o editor original
            if self.canvas and self.canvas.winfo_manager():
                self.canvas.grid_remove()
                if self.info_bar: self.info_bar.place_forget()
                
                editor = self.ctx.editor
                if editor:
                    editor.textbox.grid(row=0, column=2, sticky="nsew")
                    editor.line_numbers.grid(row=0, column=0, sticky="ns")
                    editor.git_margin.grid(row=0, column=1, sticky="ns")
                    editor.grid_rowconfigure(0, weight=1)

    def toggle_view(self):
        path = self.ctx.current_file
        if not path or not self.ctx.editor: return

        editor = self.ctx.editor
        active = self.is_active.get(path, False)

        if not self.canvas:
            theme_bg = self.ctx.theme.get("editor", {}).get("bg", "#1e1e1e")
            self.canvas = ImageViewerCanvas(editor, bg=theme_bg)
            self.info_bar = ctk.CTkLabel(editor, text="", font=("Segoe UI", 10), fg_color="#21252b")

        if not active:
            # Entrar em modo visualização
            editor.textbox.grid_remove()
            editor.line_numbers.grid_remove()
            editor.git_margin.grid_remove()

            self.canvas.grid(row=0, column=0, columnspan=3, sticky="nsew")
            self.canvas.load_image(path)
            
            # Atualiza info da imagem
            img = self.canvas.image_raw
            size = os.path.getsize(path) / 1024
            self.info_bar.configure(text=f" 󰋩 {img.width}x{img.height} | {size:.1f} KB | Zoom: {int(self.canvas.scale*100)}%")
            self.info_bar.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=10)

            self.is_active[path] = True
            self.btn_toggle.configure(fg_color="#1f538d", text="Ver Texto")
        else:
            # Voltar para o editor
            self.canvas.grid_remove()
            self.info_bar.place_forget()
            
            editor.textbox.grid(row=0, column=2, sticky="nsew")
            editor.line_numbers.grid(row=0, column=0, sticky="ns")
            editor.git_margin.grid(row=0, column=1, sticky="ns")

            self.is_active[path] = False
            self.btn_toggle.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="Visualizar Imagem")

def setup(ctx: AppContext):
    """Ponto de entrada do plugin."""
    plugin = ImagePlugin(ctx)
    ctx.external_plugins.append(plugin)
    
    # Monkey-patching no editor para detectar troca de arquivo
    # Uma alternativa melhor seria um sistema de eventos, mas isso resolve para plugins externos.
    if ctx.editor:
        orig_set_text = ctx.editor.set_text
        def wrapped_set_text(text: str):
            orig_set_text(text)
            plugin.update_visibility()
        ctx.editor.set_text = wrapped_set_text
    
    plugin.update_visibility()
    print("[PLUGIN] Image Viewer inicializado.")