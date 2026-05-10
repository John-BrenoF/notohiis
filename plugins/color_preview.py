import re
import tkinter as tk
from core.src.app_context import AppContext

class ColorPreviewPlugin:
    """
    Plugin que identifica códigos de cores hexadecimais em arquivos JSON/CSS/PY
    e aplica um realce visual (fundo colorido) no próprio texto.
    """
    def __init__(self, ctx):
        self.ctx = ctx
        # Regex para capturar hex codes: #RGB, #RGBA, #RRGGBB, #RRGGBBAA
        self.pattern = re.compile(r'#(?:[0-9a-fA-F]{3,4}){1,2}\b')

    def run(self):
        if not self.ctx.current_file:
            return

        # Filtra por extensões onde cores hex são comuns
        ext = self.ctx.current_file.lower()
        if not (ext.endswith(".json") or ext.endswith(".css") or ext.endswith(".py") or ext.endswith(".html")):
            return

        editor = self.ctx.editor_container
        if not editor or not hasattr(editor, "textbox"):
            return

        txt = editor.textbox._textbox
        content = txt.get("1.0", tk.END)

        # Limpa tags de cores antigas para re-renderizar
        for tag in txt.tag_names():
            if tag.startswith("hex_"):
                txt.tag_delete(tag)

        for match in self.pattern.finditer(content):
            color_code = match.group()
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            
            # Tag única por ocorrência para evitar conflitos de estilo
            tag_name = f"hex_{color_code}_{match.start()}"
            txt.tag_add(tag_name, start, end)
            
            try:
                # Lógica de contraste para garantir que o texto continue legível
                r = int(color_code[1:3], 16) if len(color_code) > 4 else int(color_code[1]*2, 16)
                g = int(color_code[3:5], 16) if len(color_code) > 4 else int(color_code[2]*2, 16)
                b = int(color_code[5:7], 16) if len(color_code) > 4 else int(color_code[3]*2, 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                fg = "#000000" if luminance > 0.5 else "#ffffff"
                
                txt.tag_configure(tag_name, background=color_code, foreground=fg)
            except:
                continue

def setup(ctx):
    """Função de entrada para o carregador de plugins."""
    plugin = ColorPreviewPlugin(ctx)
    ctx.external_plugins.append(plugin)