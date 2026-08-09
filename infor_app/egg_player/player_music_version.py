import os
import signal
import subprocess
import time
import math
import random
import tkinter as tk
import customtkinter as ctk

class MusicPlayerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Player")
        self.geometry("320x420")
        self.configure(fg_color="#000000")
        self.resizable(False, False)
        self._center_window(320, 420)

        self.music_process = None
        self.is_playing = False
        self.duration = 180.0
        self.elapsed = 0.0
        self.last_update = time.time()
        self.anim_time = 0.0

        self._setup_ui()
        self._start_music()
        self._animate()
        self._update_progress()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, width, height):
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        self.canvas = tk.Canvas(self, width=320, height=280, bg="#000000", highlightthickness=0)
        self.canvas.pack(pady=(10, 0))

        progress_frame = ctk.CTkFrame(self, fg_color="#000000")
        progress_frame.pack(fill="x", padx=20, pady=(10, 2))

        self.time_lbl = ctk.CTkLabel(progress_frame, text="00:00", font=("Consolas", 11), text_color="#888888")
        self.time_lbl.pack(side="left")

        self.rem_lbl = ctk.CTkLabel(progress_frame, text="-00:00", font=("Consolas", 11), text_color="#888888")
        self.rem_lbl.pack(side="right")

        self.prog_bg = tk.Canvas(self, height=4, bg="#1e1e2e", highlightthickness=0)
        self.prog_bg.pack(fill="x", padx=20, pady=(2, 10))
        self.prog_bar = self.prog_bg.create_rectangle(0, 0, 0, 4, fill="#61afef", width=0)

        self.play_btn = ctk.CTkButton(
            self, text="PAUSE", width=100, height=32, corner_radius=16,
            fg_color="#2b2d3a", hover_color="#3a3c4d", text_color="#ffffff",
            font=("Segoe UI", 11, "bold"),
            command=self._toggle_play
        )
        self.play_btn.pack(pady=5)

    def _get_duration(self, path):
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True
            )
            return float(res.stdout.strip())
        except Exception:
            return 180.0 

    def _start_music(self):
        music_path = os.path.join(os.getcwd(), "infor_app", "musics", "Lost(hkmori)_(0.5aplha).mp3")
        if not os.path.exists(music_path):
            return

        self.duration = self._get_duration(music_path)
        
        try:
            self.music_process = subprocess.Popen(
                ["mpv", "--no-video", music_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.is_playing = True
            self.last_update = time.time()
        except FileNotFoundError:
            try:
                self.music_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", music_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self.is_playing = True
                self.last_update = time.time()
            except FileNotFoundError:
                pass

    def _toggle_play(self):
        if not self.music_process:
            return

        if self.is_playing:
            os.kill(self.music_process.pid, signal.SIGSTOP)
            self.is_playing = False
            self.play_btn.configure(text="PLAY")
        else:
            os.kill(self.music_process.pid, signal.SIGCONT)
            self.is_playing = True
            self.last_update = time.time()
            self.play_btn.configure(text="PAUSE")

    def _update_progress(self):
        if self.is_playing:
            now = time.time()
            self.elapsed += (now - self.last_update)
            self.last_update = now

            if self.elapsed > self.duration:
                self.elapsed = self.duration
                self.is_playing = False
                self.play_btn.configure(text="PLAY")

        if self.duration > 0:
            pct = min(1.0, self.elapsed / self.duration)
            w = self.prog_bg.winfo_width()
            self.prog_bg.coords(self.prog_bar, 0, 0, int(w * pct), 4)

        rem = max(0, self.duration - self.elapsed)
        
        em, es = int(self.elapsed // 60), int(self.elapsed % 60)
        rm, rs = int(rem // 60), int(rem % 60)
        
        self.time_lbl.configure(text=f"{em:02d}:{es:02d}")
        self.rem_lbl.configure(text=f"-{rm:02d}:{rs:02d}")

        self.after(100, self._update_progress)

    def _animate(self):
        self.canvas.delete("all")
        
        if self.is_playing:
            self.anim_time += 0.15

        num_pillars = 18
        w = 320 / num_pillars
        points = []

        for i in range(num_pillars):
            if self.is_playing:
                wave = math.sin(self.anim_time + i * 0.4) * math.cos(self.anim_time * 0.6 - i * 0.2)
                noise = random.uniform(0.7, 1.3)
                val = abs(wave) * noise
            else:
                val = 0.02 
            
            height = 5 + val * 200
            
            x0 = i * w + 3
            x1 = x0 + w - 6
            y1 = 280
            y0 = y1 - height

            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#121216", outline="#61afef", width=1)
            
            cx = (x0 + x1) / 2
            points.append(cx)
            points.append(y0)

        if len(points) >= 4:
            self.canvas.create_line(*points, fill="#c678dd", width=2, smooth=True)
            self.canvas.create_line(*[p + (5 if i % 2 == 1 else 0) for i, p in enumerate(points)], fill="#98c379", width=1, smooth=True, dash=(2, 4))

        self.after(35, self._animate)

    def _on_close(self):
        if self.music_process:
            try:
                self.music_process.terminate()
            except Exception:
                pass
        self.destroy()

if __name__ == "__main__":
    app = MusicPlayerWindow()
    app.mainloop()