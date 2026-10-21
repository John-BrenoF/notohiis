import bisect
import hashlib
import re

from notohiis_core import AppContext, CONTENT_CHANGED, FILE_CHANGED, THEME_CHANGED


class RustSyntaxLexer:
    ALTERNATIVAS = (
        r'(?P<texto_bruto>\b(?:br|cr)?r#*"(?:[^"]|"(?!#))*"#*)',
        r'(?P<texto>"(?:\\.|[^"\\\n])*")',
        r"(?P<comentario_bloco>/\*[\s\S]*?\*/)",
        r"(?P<comentario_linha>//[^\n]*)",
        r"""(?P<literal_char>'(?:\\.|[^'\\])')""",
        r"""(?P<lifetime>'[A-Za-z_]\w*)""",
        r"(?P<atributo>#!?\[)",
        r"(?P<definicao>\b(?:fn|struct|enum|trait|type|mod|union|impl)\b\s+)"
        r"(?P<def_nome>[A-Za-z_]\w*)",
        r"(?P<macro_nome>\b[a-z_]\w*!)",
        r"(?P<mesmo>\bself\b)",
        r"(?P<keyword>\b(?:as|async|await|break|const|continue|crate|dyn|else|enum"
        r"|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return"
        r"|static|struct|super|trait|true|type|union|unsafe|use|where|while|Self|box"
        r"|do|final|macro|override|priv|typeof|unsized|virtual|yield|try|abstract"
        r"|become)\b)",
        r"(?P<tipo>\b(?:bool|char|str|i8|i16|i32|i64|i128|isize|u8|u16|u32|u64"
        r"|u128|usize|f32|f64|String|Vec|Option|Result|Box|Rc|Arc|Cow|Cell|RefCell"
        r"|Mutex|RwLock|HashMap|HashSet|BTreeMap|BTreeSet|Path|PathBuf|OsString"
        r"|Ordering|Error|Iterator|Some|None|Ok|Err|Copy|Clone|Debug|Default|Display"
        r"|Drop|From|Into|ToString)\b)",
        r"(?P<numero>\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+"
        r"|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?)"
        r"(?:[iu](?:8|16|32|64|128|size)|f(?:32|64))?)",
    )

    TAG_POR_GRUPO = {
        "texto_bruto": "string",
        "texto": "string",
        "literal_char": "string",
        "comentario_bloco": "comment",
        "comentario_linha": "comment",
        "lifetime": "definition",
        "def_nome": "definition",
        "mesmo": "definition",
        "atributo": "keyword",
        "definicao": "keyword",
        "keyword": "keyword",
        "macro_nome": "builtin",
        "tipo": "builtin",
        "numero": "number",
    }

    MESTRE = re.compile("|".join(ALTERNATIVAS))

    def extract(self, conteudo, validas):
        tokens = []
        for casamento in self.MESTRE.finditer(conteudo):
            for nome, tag in self.TAG_POR_GRUPO.items():
                if tag not in validas:
                    continue
                if casamento.group(nome) is None:
                    continue
                tokens.append((tag, casamento.start(nome), casamento.end(nome)))
        return tokens


class RustSyntaxPlugin:
    CORES_PADRAO = {
        "keyword": "#ff79c6",
        "builtin": "#8be9fd",
        "string": "#f1fa8c",
        "comment": "#6272a4",
        "number": "#bd93f9",
        "definition": "#50fa7b",
    }

    def __init__(self, ctx):
        self.ctx = ctx
        self.lexer = RustSyntaxLexer()
        self.tags = tuple(self.CORES_PADRAO)
        self.assinatura = None

    def _cores(self):
        cores = dict(self.CORES_PADRAO)
        try:
            cores.update(self.ctx.theme.get("syntax", {}) or {})
        except Exception:
            pass
        return cores

    def configurar_tags(self):
        editor = self.ctx.editor
        if not editor:
            return
        for nome_tag, cor in self._cores().items():
            if cor:
                editor.configure_tag(nome_tag, foreground=cor)

    def _inicios_de_linha(self, conteudo):
        inicios = [0]
        for casamento in re.finditer("\n", conteudo):
            inicios.append(casamento.end())
        return inicios

    def _indice_tk(self, deslocamento, inicios):
        linha = bisect.bisect_right(inicios, deslocamento) - 1
        coluna = deslocamento - inicios[linha]
        return f"{linha + 1}.{coluna}"

    def _limpar(self):
        editor = self.ctx.editor
        self.assinatura = None
        if not editor:
            return
        for nome_tag in self.tags:
            editor.remove_tag(nome_tag, "1.0", "end")

    def _destacar(self, conteudo):
        editor = self.ctx.editor
        arquivo = self.ctx.current_file
        if not editor or not arquivo:
            return
        if not str(arquivo).endswith(".rs"):
            return
        digest = hashlib.md5(
            conteudo.encode("utf-8", errors="ignore")
        ).hexdigest()
        assinatura = (str(arquivo), digest)
        if assinatura == self.assinatura:
            return
        cores = self._cores()
        validas = {
            tag for tag in self.lexer.TAG_POR_GRUPO.values() if cores.get(tag)
        }
        for nome_tag in validas:
            editor.remove_tag(nome_tag, "1.0", "end")
        inicios = self._inicios_de_linha(conteudo)
        for nome_tag, inicio, fim in self.lexer.extract(conteudo, validas):
            editor.apply_tag(
                nome_tag,
                self._indice_tk(inicio, inicios),
                self._indice_tk(fim, inicios),
            )
        self.assinatura = assinatura

    def ao_mudar_arquivo(self, arquivo):
        try:
            self.assinatura = None
            self.configurar_tags()
            editor = self.ctx.editor
            if editor and arquivo and str(arquivo).endswith(".rs"):
                self._destacar(editor.get_text())
            else:
                self._limpar()
        except Exception as erro:
            print(f"[RUST SYNTAX] ao_mudar_arquivo: {erro}")

    def ao_mudar_conteudo(self, conteudo):
        try:
            if conteudo is None:
                return
            self._destacar(conteudo)
        except Exception as erro:
            print(f"[RUST SYNTAX] ao_mudar_conteudo: {erro}")

    def ao_mudar_tema(self, *args):
        try:
            self.configurar_tags()
        except Exception as erro:
            print(f"[RUST SYNTAX] ao_mudar_tema: {erro}")


def setup(ctx: AppContext):
    plugin = RustSyntaxPlugin(ctx)
    ctx.external_plugins.append(plugin)
    ctx.events.on(FILE_CHANGED, plugin.ao_mudar_arquivo)
    ctx.events.on(CONTENT_CHANGED, plugin.ao_mudar_conteudo)
    ctx.events.on(THEME_CHANGED, plugin.ao_mudar_tema)
    plugin.ao_mudar_arquivo(ctx.current_file)
    return None
