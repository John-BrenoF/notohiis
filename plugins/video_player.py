"""
Plugin de reprodução de vídeo para o editor Notohiis.
Suporta reprodução assíncrona, busca (seek) e redimensionamento dinâmico.
Dependências: pip install opencv-python Pillow
"""

import os
import threading
import queue
import time
from typing import Optional
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from core.src.app_context import AppContext

class VideoPlayerCanvas(ctk.CTkCanvas):
    """Canvas otimizado para exibição de frames de vídeo."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.photo = None

    def update_frame(self, image: Image.Image):
        """Redimensiona e desenha o frame centralizado."""
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()

        if canvas_w > 1 and canvas_h > 1:
            # Manter Aspect Ratio
            img_w, img_h = image.size
            scale = min(canvas_w / img_w, canvas_h / img_h)
            
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            if new_w > 0 and new_h > 0:
                resized = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                self.photo = ImageTk.PhotoImage(resized)
                
                self.delete("all")
                x = (canvas_w - new_w) // 2
                y = (canvas_h - new_h) // 2
                self.create_image(x, y, image=self.photo, anchor="nw")

class VideoPlayerPlugin:
    """Lógica principal do player de vídeo."""
    EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv'}

    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.player_frame = None
        self.is_active = {}
        
        # Controle de Vídeo
        self.cap = None
        self.cap_lock = threading.Lock()
        self.frame_queue = queue.Queue(maxsize=10)
        self.playing = False
        self.stop_event = threading.Event()
        self.fps = 30
        self.total_frames = 0
        self.current_frame_idx = 0

    def _inject_ui(self):
        if not hasattr(self, 'btn_view') and self.ctx.status_bar:
            self.btn_view = ctk.CTkButton(
                self.ctx.status_bar,
                text="Assistir Vídeo",
                width=100, height=20,
                font=("Segoe UI", 10),
                command=self.toggle_player
            )

    def update_visibility(self):
        self._inject_ui()
        if not hasattr(self, 'btn_view'): return

        path = self.ctx.current_file
        if path and os.path.splitext(path)[1].lower() in self.EXTENSIONS:
            self.btn_view.pack(side="right", padx=10)
        else:
            self.btn_view.pack_forget()
            if self.player_frame and self.player_frame.winfo_manager():
                self.toggle_player() # Força fechamento se mudar para arquivo não-vídeo

    def _create_widgets(self):
        editor = self.ctx.editor
        self.player_frame = ctk.CTkFrame(editor, fg_color="#000000")
        
        self.canvas = VideoPlayerCanvas(self.player_frame, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Barra de Controles
        controls = ctk.CTkFrame(self.player_frame, height=40, fg_color="#1a1a1a")
        controls.pack(fill="x", side="bottom")

        self.btn_play = ctk.CTkButton(controls, text="▶", width=40, command=self._toggle_play)
        self.btn_play.pack(side="left", padx=10, pady=5)

        self.slider = ctk.CTkSlider(controls, from_=0, to=100, command=self._on_seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)

        self.time_label = ctk.CTkLabel(controls, text="00:00 / 00:00", font=("Segoe UI", 10))
        self.time_label.pack(side="right", padx=10)

    def toggle_player(self):
        path = self.ctx.current_file
        if not path or not self.ctx.editor: return

        editor = self.ctx.editor
        active = self.is_active.get(path, False)

        if not self.player_frame:
            self._create_widgets()

        if not active:
            # Ativar Player
            editor.textbox.grid_remove()
            editor.line_numbers.grid_remove()
            editor.git_margin.grid_remove()
            self.player_frame.grid(row=0, column=0, columnspan=3, sticky="nsew")
            
            self._load_video(path)
            self.is_active[path] = True
            self.btn_view.configure(fg_color="#1f538d", text="Ver Texto")
        else:
            # Voltar Editor
            self._stop_playback()
            self.player_frame.grid_remove()
            editor.textbox.grid(row=0, column=2, sticky="nsew")
            editor.line_numbers.grid(row=0, column=0, sticky="ns")
            editor.git_margin.grid(row=0, column=1, sticky="ns")
            
            self.is_active[path] = False
            self.btn_view.configure(fg_color=["#3B8ED0", "#1F6AA5"], text="Assistir Vídeo")

    def _load_video(self, path):
        with self.cap_lock:
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened(): return

            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            
        self.slider.configure(to=self.total_frames)
        
        self.stop_event.clear()
        self.playing = True
        self.btn_play.configure(text="⏸")
        
        # Inicia thread de leitura
        threading.Thread(target=self._reader_thread, daemon=True).start()
        # Inicia loop de atualização da UI
        self._update_ui_loop()

    def _reader_thread(self):
        """Thread para decodificar frames sem travar a UI."""
        while not self.stop_event.is_set() and self.cap:
            if self.playing:
                with self.cap_lock:
                    ret, frame = self.cap.read()
                    if not ret:
                        self.playing = False
                        break
                    
                    self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                
                # Conversão BGR -> RGB -> PIL
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                
                try:
                    self.frame_queue.put(img, timeout=1.0)
                except queue.Full:
                    continue
                
                time.sleep(1/self.fps)
            else:
                time.sleep(0.1)

    def _update_ui_loop(self):
        """Loop na thread principal para desenhar os frames."""
        if self.stop_event.is_set(): return

        try:
            img = self.frame_queue.get_nowait()
            self.canvas.update_frame(img)
            
            # Atualiza Barra de Progresso e Tempo
            self.slider.set(self.current_frame_idx)
            curr_sec = self.current_frame_idx / self.fps
            total_sec = self.total_frames / self.fps
            self.time_label.configure(text=f"{self._fmt_time(curr_sec)} / {self._fmt_time(total_sec)}")
        except queue.Empty:
            pass

        self.ctx.window.after(10, self._update_ui_loop)

    def _toggle_play(self):
        self.playing = not self.playing
        self.btn_play.configure(text="⏸" if self.playing else "▶")

    def _on_seek(self, val):
        if self.cap and self.cap.isOpened():
            with self.cap_lock:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(val))
                # Limpa a queue para o novo ponto evitando frames residuais
                while not self.frame_queue.empty():
                    try: self.frame_queue.get_nowait()
                    except queue.Empty: break

    def _stop_playback(self):
        self.stop_event.set()
        self.playing = False
        with self.cap_lock:
            if self.cap:
                self.cap.release()
                self.cap = None
        while not self.frame_queue.empty(): self.frame_queue.get()

    def _fmt_time(self, s):
        return f"{int(s//60):02d}:{int(s%60):02d}"

def setup(ctx: AppContext):
    plugin = VideoPlayerPlugin(ctx)
    ctx.external_plugins.append(plugin)

    if ctx.editor:
        orig_set_text = ctx.editor.set_text
        def wrapped_set_text(text: str):
            orig_set_text(text)
            plugin.update_visibility()
        ctx.editor.set_text = wrapped_set_text

    plugin.update_visibility()
    print("[PLUGIN] Video Player carregado.")