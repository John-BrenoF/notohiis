import re
from core.src.app_context import AppContext

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
        self.applied_tags = set()
        self._after_id = None

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
        self._process_matches(editor, self.rgb_pattern.finditer(content), is_hex=False)

    def _process_matches(self, editor, matches, is_hex=True):
        for match in matches:
            raw_color = match.group()
            try:
                # Converte para RGB para calcular contraste e normalizar para o Tkinter
                if is_hex:
                    if len(raw_color) not in (4, 5, 7, 9): continue
                    r, g, b = self._hex_to_rgb(raw_color)
                    tk_color = raw_color[:7] if len(raw_color) > 5 else raw_color # Tkinter não ama hex de 8 chars
                else:
                    # Extrai números de rgb(255, 0, 0)
                    nums = [int(n) for n in re.findall(r'\d+', raw_color)[:3]]
                    r, g, b = [max(0, min(255, n)) for n in nums] # Clamp 0-255
                    tk_color = f'#{r:02x}{g:02x}{b:02x}'

                start_pos = editor.index_offset("1.0", match.start())
                end_pos = editor.index_offset("1.0", match.end())
                
                tag_name = f"cp_{match.start()}"
                editor.apply_tag(tag_name, start_pos, end_pos)
                self.applied_tags.add(tag_name)
                
                fg = self._get_contrast_fg(r, g, b)
                editor.configure_tag(tag_name, background=tk_color, foreground=fg)
            except Exception:
                continue

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