import re
import colorsys
from tkinter import colorchooser
from core.src.app_context import AppContext
import tkinter as tk

class ColorPreviewPlugin:
    """
    Plugin que identifica códigos de cores hexadecimais em arquivos JSON/CSS/PY
    e aplica um realce visual (fundo colorido) no próprio texto.
    Aprimorado com debouncing e gerenciamento eficiente de memória de tags.
    """
    def __init__(self, ctx):
        self.ctx = ctx
        # Regex para Hexadecimais
        self.hex_pattern = re.compile(r'#(?:[0-9a-fA-F]{3,4}){1,2}\b')
        # Regex para rgb() e rgba()
        self.rgb_pattern = re.compile(r'rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}(?:\s*,\s*[0-9.]+\s*)?\)')
        # Regex para hsl() e hsla()
        self.hsl_pattern = re.compile(r'hsla?\(\s*\d{1,3}\s*,\s*\d{1,3}%\s*,\s*\d{1,3}%\s*(?:\s*,\s*[0-9.]+\s*)?\)')
        # Lista de nomes de cores CSS comuns
        color_names = [
            "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond",
            "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue",
            "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkkhaki",
            "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
            "darkslateblue", "darkslategray", "darkturquoise", "darkviolet", "deeppink", "deepskyblue", "dimgray",
            "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold",
            "goldenrod", "gray", "green", "greenyellow", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki",
            "lavender", "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan", "lightgray",
            "lightgreen", "lightpink", "lightsalmon", "lightseagreen", "lightskyblue", "lightslategray", "lightsteelblue",
            "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue", "mediumorchid",
            "mediumpurple", "mediumseagreen", "mediumslateblue", "mediumspringgreen", "mediumturquoise", "mediumvioletred",
            "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab",
            "orange", "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred", "papayawhip",
            "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "red", "rosybrown", "royalblue", "saddlebrown",
            "salmon", "sandybrown", "seagreen", "seashell", "sienna", "silver", "skyblue", "slateblue", "slategray", "snow",
            "springgreen", "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white",
            "whitesmoke", "yellow", "yellowgreen"
        ]
        self.name_pattern = re.compile(r'\b(' + '|'.join(color_names) + r')\b', re.IGNORECASE)
        
        self.applied_tags = set()
        self._after_id = None
        self._setup_events()

    def _setup_events(self):
        """Configura o evento de clique para o Color Picker."""
        if self.ctx.editor and hasattr(self.ctx.editor, "textbox"):
            # Bind direto no widget interno do Tkinter para capturar coordenadas exatas
            self.ctx.editor.textbox._textbox.bind("<Button-1>", self._on_editor_click, add="+")

    def run(self):
        """Ponto de entrada chamado a cada modificação no editor."""
        if not self.ctx.current_file or not self.ctx.editor:
            return

        # Extensões onde realce de cores é produtivo
        ext = self.ctx.current_file.lower()
        valid_extensions = (".json", ".css", ".py", ".html", ".js", ".ts", ".jsx", ".tsx", ".yaml")
        if not any(ext.endswith(e) for e in valid_extensions):
            return

        # Debounce: evita reprocessar a cada tecla, melhorando a performance em arquivos grandes
        if self._after_id:
            try: self.ctx.window.after_cancel(self._after_id)
            except: pass
        
        self._after_id = self.ctx.window.after(350, self._apply_colors)

    def _apply_colors(self):
        editor = self.ctx.editor
        if not editor: return

        content = editor.get_text()

        # Limpa apenas as tags gerenciadas por este plugin
        for tag in list(self.applied_tags):
            editor.delete_tag(tag)
        self.applied_tags.clear()

        # Processa ambos os padrões
        self._process_matches(editor, self.hex_pattern.finditer(content), is_hex=True)
        self._process_matches(editor, self.rgb_pattern.finditer(content), is_hex=False, is_rgb=True)
        self._process_matches(editor, self.hsl_pattern.finditer(content), is_hex=False, is_rgb=False, is_hsl=True)
        self._process_matches(editor, self.name_pattern.finditer(content), is_hex=False, is_rgb=False)

    def _process_matches(self, editor, matches, is_hex=True, is_rgb=False, is_hsl=False):
        for match in matches:
            raw_color = match.group()
            try:
                if is_hex:
                    if len(raw_color) not in (4, 5, 7, 9): continue
                    r, g, b = self._hex_to_rgb(raw_color)
                    tk_color = raw_color[:7] if len(raw_color) > 5 else raw_color # Tkinter não ama hex de 8 chars
                elif is_rgb:
                    # Extrai números de rgb(255, 0, 0)
                    nums = [int(n) for n in re.findall(r'\d+', raw_color)[:3]]
                    r, g, b = [max(0, min(255, n)) for n in nums] # Clamp 0-255
                    tk_color = f'#{r:02x}{g:02x}{b:02x}'
                elif is_hsl:
                    # Extrai números de hsl(0, 100%, 50%)
                    nums = [float(n) for n in re.findall(r'[0-9.]+', raw_color)[:3]]
                    r, g, b = self._hsl_to_rgb(nums[0], nums[1], nums[2])
                    tk_color = f'#{r:02x}{g:02x}{b:02x}'
                else:
                    # Cores por nome: Resolve via winfo_rgb do widget
                    tk_color = raw_color.lower()
                    rgb_tuple = editor.textbox._textbox.winfo_rgb(tk_color)
                    r, g, b = [c >> 8 for c in rgb_tuple] # Tkinter retorna 16-bit, convertemos para 8-bit

                start_pos = editor.index_offset("1.0", match.start())
                end_pos = editor.index_offset("1.0", match.end())
                
                # Usamos um prefixo 'cp_' para identificar tags deste plugin
                tag_name = f"cp_{match.start()}_{len(raw_color)}"
                editor.apply_tag(tag_name, start_pos, end_pos)
                self.applied_tags.add(tag_name)
                
                fg = self._get_contrast_fg(r, g, b)
                editor.configure_tag(tag_name, background=tk_color, foreground=fg)
            except Exception:
                continue

    def _on_editor_click(self, event):
        """Detecta clique em uma tag de cor e abre o seletor."""
        editor = self.ctx.editor
        if not editor: return

        # Identifica tags sob o clique
        tags = editor.textbox._textbox.tag_names(f"@{event.x},{event.y}")
        color_tag = next((t for t in tags if t.startswith("cp_")), None)

        if color_tag:
            # Obtém a cor atual do texto sob a tag
            ranges = editor.textbox._textbox.tag_ranges(color_tag)
            if not ranges: return
            
            start, end = ranges[0], ranges[1]
            current_color_str = editor.get_text(start, end)

            # Abre o seletor de cores
            new_color = colorchooser.askcolor(initialcolor=current_color_str, title="Seletor de Cores - Notohiis")
            
            if new_color[1]: # Se o usuário confirmou (não cancelou)
                # Substitui no editor
                editor.delete(start, end)
                editor.insert(new_color[1], start)
                # Dispara o processamento para atualizar a tag imediatamente
                self._apply_colors()
                return "break"

    def _hsl_to_rgb(self, h, s, l):
        """Converte HSL (0-360, 0-100, 0-100) para RGB (0-255)."""
        r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
        return int(r * 255), int(g * 255), int(b * 255)

    def _hex_to_rgb(self, hex_code):
        """Converte string hex para tupla (r, g, b)."""
        h = hex_code.lstrip('#')
        if len(h) <= 4:
            return tuple(int(h[i]*2, 16) for i in (0, 1, 2))
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _get_contrast_fg(self, r, g, b):
        """Calcula se o texto deve ser preto ou branco."""
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        return "#000000" if luminance > 0.5 else "#ffffff"

def setup(ctx):
    """Função de entrada para o carregador de plugins."""
    plugin = ColorPreviewPlugin(ctx)
    ctx.external_plugins.append(plugin)