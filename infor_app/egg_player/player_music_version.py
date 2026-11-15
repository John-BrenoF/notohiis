#______________[português]____________________
# Copyright (c) 2026 John-BrenoF
# Este programa é um software livre: você pode redistribuí-lo e/ou modificá-lo
# sob os termos da licença LUMEJ v1.0. Veja o arquivo LICENSE no repositório.
#_____________[english]____________________
# Copyright (c) 2016-2026 John-BrenoF
# This program is free software: you can redistribute it and/or modify it
# under the terms of the LUMEJ v1.0 license. See the LICENSE file in the repository.

import io
import json
import math
import os
import random
import signal
import subprocess
import time
import tkinter as tk
import webbrowser

import customtkinter as ctk
from PIL import Image, ImageDraw

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MUSICA_EGG = os.path.join(
    _APP_ROOT, "infor_app", "musics", "frxgxd - 1553470665499594756(MP3_160K)(0.6 alfa).mp3"
)
LINK_ARTISTA_JSON = os.path.join(_APP_ROOT, "infor_app", "musics", "link.json")

LARGURA_JANELA = 340
ALTURA_INICIAL_JANELA = 720
MARGEM_INFERIOR = 14
TAMANHO_CAPA = 176
LARGURA_VISUALIZADOR = 300
ALTURA_VISUALIZADOR = 150
DURACAO_PADRAO = 180.0


def _ffprobe_json(caminho, entradas):
    try:
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", entradas, "-of", "json", caminho],
            capture_output=True, text=True, timeout=15,
        )
        return json.loads(saida.stdout or "{}")
    except Exception:
        return {}


def _clean_tag(valor):
    if not isinstance(valor, str):
        return ""
    return valor.replace("\ufeff", "").strip()


def _read_track_info(caminho):
    dados = _ffprobe_json(caminho, "format=duration:format_tags").get("format", {})
    tags = dados.get("tags") or {}
    titulo = _clean_tag(tags.get("title")) or os.path.splitext(os.path.basename(caminho))[0]
    artista = _clean_tag(tags.get("artist")) or "Artista desconhecido"
    try:
        duracao = float(dados.get("duration") or DURACAO_PADRAO)
    except (TypeError, ValueError):
        duracao = DURACAO_PADRAO
    return {"title": titulo, "artist": artista, "duration": duracao}


def _extract_cover(caminho):
    try:
        saida = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", caminho, "-an", "-map", "0:v:0",
             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
            capture_output=True, timeout=15,
        )
        if not saida.stdout:
            return None
        return Image.open(io.BytesIO(saida.stdout)).convert("RGB")
    except Exception:
        return None


def _square_cover(imagem):
    lado = min(imagem.size)
    esquerda = (imagem.width - lado) // 2
    topo = (imagem.height - lado) // 2
    recorte = imagem.crop((esquerda, topo, esquerda + lado, topo + lado))
    return recorte.resize((TAMANHO_CAPA, TAMANHO_CAPA), Image.LANCZOS)


def _round_corners(imagem):
    mascara = Image.new("L", (TAMANHO_CAPA, TAMANHO_CAPA), 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, TAMANHO_CAPA - 1, TAMANHO_CAPA - 1), radius=16, fill=255
    )
    arredondada = imagem.convert("RGBA")
    arredondada.putalpha(mascara)
    return arredondada


def _default_cover():
    fundo = Image.new("RGBA", (TAMANHO_CAPA, TAMANHO_CAPA), (30, 31, 46, 255))
    desenho = ImageDraw.Draw(fundo)
    nota = (97, 175, 239, 255)
    desenho.ellipse((34, 112, 76, 144), fill=nota)
    desenho.rectangle((70, 44, 76, 128), fill=nota)
    desenho.ellipse((98, 100, 140, 132), fill=nota)
    desenho.rectangle((134, 32, 140, 116), fill=nota)
    desenho.polygon([(70, 44), (140, 32), (140, 48), (70, 60)], fill=nota)
    return _round_corners(fundo)


def _load_cover(caminho):
    imagem = _extract_cover(caminho)
    if imagem is None:
        return _default_cover()
    return _round_corners(_square_cover(imagem))


def _read_artist_link():
    try:
        with open(LINK_ARTISTA_JSON, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError):
        return None
    link = dados.get("link_do_artista") if isinstance(dados, dict) else None
    if not isinstance(link, str) or not link.strip():
        return None
    return link.strip()


def _open_artist_link(link):
    if os.environ.get("FLATPAK_ID"):
        try:
            subprocess.Popen(
                ["flatpak-spawn", "--host", "xdg-open", link],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        except OSError:
            pass
    try:
        webbrowser.open(link)
    except Exception:
        pass


class MusicPlayerWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Player")
        self.geometry(f"{LARGURA_JANELA}x{ALTURA_INICIAL_JANELA}")
        self.configure(fg_color="#0d0d0d")
        self.resizable(False, False)

        self.music_process = None
        self.is_playing = False
        self.duration = DURACAO_PADRAO
        self.elapsed = 0.0
        self.last_update = time.time()
        self.anim_time = 0.0
        self.music_path = MUSICA_EGG
        self.track_info = _read_track_info(self.music_path)
        self.artist_link = _read_artist_link()

        self._setup_ui()
        self._fit_window_height()
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
        self._setup_cover()
        self._setup_track_info()
        self._setup_visualizer()
        self._setup_controls()

    def _fit_window_height(self):
        self.update_idletasks()
        altura = (
            self.play_button.winfo_y()
            + self.play_button.winfo_height()
            + MARGEM_INFERIOR
        )
        self.geometry(f"{LARGURA_JANELA}x{altura}")
        self._center_window(LARGURA_JANELA, altura)

    def _setup_cover(self):
        self.cover_frame = ctk.CTkFrame(
            self,
            fg_color="#1a1a1a",
            corner_radius=8,
            width=TAMANHO_CAPA,
            height=TAMANHO_CAPA
        )
        self.cover_frame.pack(pady=(16, 12))
        self.cover_frame.pack_propagate(False)

        self.cover_image = ctk.CTkImage(
            light_image=_load_cover(self.music_path),
            size=(TAMANHO_CAPA, TAMANHO_CAPA),
        )
        self.cover_label = ctk.CTkLabel(self.cover_frame, text="", image=self.cover_image)
        self.cover_label.pack(fill="both", expand=True)

        self.video_button = ctk.CTkButton(
            self.cover_frame,
            text="▶",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#1a1a1a",
            hover_color="#333333",
            text_color="#ffffff",
            font=("Segoe UI", 10, "bold"),
            border_width=1,
            border_color="#333333",
            command=self._open_artist_video,
        )
        self.video_button.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor="se")

        if not self.artist_link:
            self.video_button.configure(state="disabled")

    def _setup_track_info(self):
        self.title_label = ctk.CTkLabel(
            self,
            text=self.track_info["title"],
            font=("Segoe UI", 13, "bold"),
            text_color="#ffffff",
            wraplength=LARGURA_JANELA - 40,
            justify="center",
        )
        self.title_label.pack()

        self.artist_label = ctk.CTkLabel(
            self,
            text=self.track_info["artist"],
            font=("Segoe UI", 11),
            text_color="#888888",
            wraplength=LARGURA_JANELA - 40,
            justify="center",
        )
        self.artist_label.pack(pady=(2, 12))

    def _open_artist_video(self):
        if self.artist_link:
            _open_artist_link(self.artist_link)

    def _setup_visualizer(self):
        self.visualizer = tk.Canvas(
            self,
            width=LARGURA_VISUALIZADOR,
            height=ALTURA_VISUALIZADOR,
            bg="#0d0d0d",
            highlightthickness=0,
        )
        self.visualizer.pack(pady=(0, 10))

    def _setup_controls(self):
        time_row = ctk.CTkFrame(self, fg_color="#0d0d0d")
        time_row.pack(fill="x", padx=24, pady=(0, 4))

        self.elapsed_label = ctk.CTkLabel(
            time_row, text="00:00", font=("Consolas", 10), text_color="#666666"
        )
        self.elapsed_label.pack(side="left")

        self.remaining_label = ctk.CTkLabel(
            time_row, text="-00:00", font=("Consolas", 10), text_color="#666666"
        )
        self.remaining_label.pack(side="right")

        self.progress_track = tk.Canvas(
            self, height=4, bg="#222222", highlightthickness=0
        )
        self.progress_track.pack(fill="x", padx=24, pady=(0, 16))
        self.progress_fill = self.progress_track.create_rectangle(
            0, 0, 0, 4, fill="#4a90e2", width=0
        )

        self.play_button = ctk.CTkButton(
            self, text="PLAY", width=120, height=36, corner_radius=8,
            fg_color="#1a1a1a", hover_color="#252525", text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
            border_width=1, border_color="#333333",
            command=self._toggle_play
        )
        self.play_button.pack(pady=(0, MARGEM_INFERIOR))

    def _start_music(self):
        if not os.path.exists(self.music_path):
            return

        self.duration = self.track_info["duration"]

        try:
            self.music_process = subprocess.Popen(
                ["mpv", "--no-video", self.music_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.is_playing = True
            self.last_update = time.time()
        except FileNotFoundError:
            try:
                self.music_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", self.music_path],
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
            self.play_button.configure(text="PLAY")
        else:
            os.kill(self.music_process.pid, signal.SIGCONT)
            self.is_playing = True
            self.last_update = time.time()
            self.play_button.configure(text="PAUSE")

    def _update_progress(self):
        if self.is_playing:
            now = time.time()
            self.elapsed += (now - self.last_update)
            self.last_update = time.time()

            if self.elapsed > self.duration:
                self.elapsed = self.duration
                self.is_playing = False
                self.play_button.configure(text="PLAY")

        if self.duration > 0:
            pct = min(1.0, self.elapsed / self.duration)
            w = self.progress_track.winfo_width()
            self.progress_track.coords(self.progress_fill, 0, 0, int(w * pct), 4)

        rem = max(0, self.duration - self.elapsed)

        em, es = int(self.elapsed // 60), int(self.elapsed % 60)
        rm, rs = int(rem // 60), int(rem % 60)

        self.elapsed_label.configure(text=f"{em:02d}:{es:02d}")
        self.remaining_label.configure(text=f"-{rm:02d}:{rs:02d}")

        self.after(100, self._update_progress)

    def _animate(self):
        self.visualizer.delete("all")

        if self.is_playing:
            self.anim_time += 0.15

        num_pillars = 18
        w = LARGURA_VISUALIZADOR / num_pillars
        points = []

        for i in range(num_pillars):
            if self.is_playing:
                wave = math.sin(self.anim_time + i * 0.4) * math.cos(self.anim_time * 0.6 - i * 0.2)
                noise = random.uniform(0.7, 1.3)
                val = abs(wave) * noise
            else:
                val = 0.02

            height = 2 + val * (ALTURA_VISUALIZADOR - 20)

            x0 = i * w + 2
            x1 = x0 + w - 4
            y1 = ALTURA_VISUALIZADOR
            y0 = y1 - height

            self.visualizer.create_rectangle(x0, y0, x1, y1, fill="#1a1a1a", outline="#333333", width=1)

            cx = (x0 + x1) / 2
            points.append(cx)
            points.append(y0)

        if len(points) >= 4:
            self.visualizer.create_line(*points, fill="#4a90e2", width=2, smooth=True)

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