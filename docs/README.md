# Notohiis Editor - Documentação Completa

![Versão](https://img.shields.io/badge/versão-0.4--alpha-blue)
![Licença](https://img.shields.io/badge/licença-GPL--3.0-green)
![Python](https://img.shields.io/badge/python-3.8+-yellow)

**Notohiis** é um editor de texto moderno, extensível e leve, desenvolvido em Python com suporte para interface gráfica (GUI) e terminal (TUI). Projetado para desenvolvedores que buscam simplicidade sem abrir mão de recursos avançados.

---

## 📋 Índice

1. [Características Principais](#características-principais)
2. [Instalação e Configuração](#instalação-e-configuração)
3. [Guia de Uso](#guia-de-uso)
4. [Arquitetura do Projeto](#arquitetura-do-projeto)
5. [Sistema de Plugins](#sistema-de-plugins)
6. [Desenvolvimento](#desenvolvimento)
7. [Atalhos de Teclado](#atalhos-de-teclado)
8. [Temas e Personalização](#temas-e-personalização)
9. [FAQ](#faq)

---

## 🚀 Características Principais

### Interface Dupla
- **GUI (CustomTkinter)**: Interface gráfica moderna e responsiva
- **TUI (Textual)**: Interface de terminal para uso remoto via SSH

### Recursos de Edição
- ✅ **Realce de Sintaxe**: Python com suporte extensível para outras linguagens
- ✅ **Autocompletar Inteligente**: Integração com LSP (Pyright) + fallback local
- ✅ **Navegação Rápida**: Alt+↑/↓ + Número (1-9) para mover cursor N linhas
- ✅ **Auto-fechamento**: Parênteses, colchetes, chaves e aspas
- ✅ **Undo/Redo Granular**: Controle atômico de transações
- ✅ **Numeração de Linhas**: Com margem Git integrada

### Gerenciamento de Arquivos
- 📁 **Explorador Lateral**: Navegação em árvore com ícones por tipo
- 📂 **Projetos Recentes**: Acesso rápido (Ctrl+R)
- 🔖 **Sistema de Abas**: Gerenciamento multi-arquivo com ocultamento inteligente
- 💾 **Sessões Persistentes**: Restaura último projeto aberto

### Integração Git
- 🔄 **Status em Tempo Real**: Indicadores visuais ([M], [A], [D])
- 📊 **Quick Commit**: Interface rápida para commits (Ctrl+G)
- 🎨 **Decoração de Arquivos**: Cores por status na sidebar

### Visualizadores Especializados
- 📝 **Markdown Preview**: Renderização HTML com tema dinâmico
- 🖼️ **Image Viewer**: Suporte a PNG, JPG, SVG com zoom e pan
- 🎬 **Video Player**: Reprodução de MP4, AVI, MKV com controles

### Plugins Avançados
- 🎨 **Color Preview**: Visualização inline de cores (hex, rgb, hsl, nomes CSS)
- 📌 **Tag Points**: Marcadores de linha com navegação (Ctrl+Alt+↑/↓)
- 🔧 **Sistema Extensível**: API para plugins externos

---

## 📦 Instalação e Configuração

### Requisitos
- Python 3.8 ou superior
- Git (para integração)
- Sistema operacional: Linux, macOS, Windows

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/notohiis.git
cd notohiis

# Execute o instalador (cria VENV e instala dependências)
chmod +x notohiis.sh
./notohiis.sh
```

O script `notohiis.sh` automaticamente:
1. Cria um ambiente virtual Python (`.venv/`)
2. Instala todas as dependências necessárias
3. Configura o alias `nth` para execução rápida

### Dependências Principais

**Core:**
- `customtkinter` - Interface gráfica moderna
- `textual` - Interface de terminal
- `Pillow` - Processamento de imagens

**Plugins:**
- `markdown2` - Renderização Markdown
- `tkinterweb` - Visualização HTML
- `opencv-python` - Reprodução de vídeo
- `svglib`, `reportlab` - Suporte SVG

### Executando o Editor

```bash
# Interface Gráfica (GUI)
nth

# Interface de Terminal (TUI)
ntht

# Abrir arquivo específico
nth arquivo.py
ntht documento.md
```

---

## 📖 Guia de Uso

### Primeira Execução

1. **Tela de Boas-Vindas**: Animação de apresentação (3 segundos)
2. **Abrir Projeto**: Ctrl+O para selecionar pasta
3. **Explorador**: Navegue pelos arquivos na sidebar esquerda
4. **Edição**: Clique em um arquivo para abrir

### Fluxo de Trabalho Típico

```
1. Abrir Projeto (Ctrl+O)
   ↓
2. Navegar na Sidebar
   ↓
3. Editar Arquivos (com autocompletar)
   ↓
4. Salvar (Ctrl+S)
   ↓
5. Commit Git (Ctrl+G)
```

### Gerenciamento de Abas

- **Abrir Nova Aba**: Ctrl+N
- **Fechar Aba**: Clique no ✕ da aba
- **Alternar Abas**: Clique na aba desejada
- **Ocultamento Inteligente**: Abas aparecem ao passar o mouse (configurável)

### Navegação Rápida

**Navegação por Linhas:**
```
Alt+↑ + 5  → Move 5 linhas para cima
Alt+↓ + 3  → Move 3 linhas para baixo
```

**Navegação por Tag Points:**
```
Ctrl+Alt+↑  → Tag anterior
Ctrl+Alt+↓  → Próximo tag
```

### Markdown Preview

1. Abra um arquivo `.md`
2. Pressione `Ctrl+M` ou clique em "View Mode"
3. Navegue pelo HTML renderizado
4. Pressione `Ctrl+M` novamente para voltar à edição

### Visualização de Imagens

1. Abra um arquivo de imagem (PNG, JPG, SVG, etc.)
2. Clique em "Visualizar Imagem" na status bar
3. Use scroll do mouse para zoom
4. Arraste com botão esquerdo para pan

---

## 🏗️ Arquitetura do Projeto

### Estrutura de Diretórios

```
notohiis/
├── core/                    # Núcleo do editor (lógica pura)
│   ├── src/                 # Componentes principais
│   │   ├── app_context.py   # Singleton de estado global
│   │   ├── buffer.py        # Gerenciamento de buffers
│   │   ├── file_manager.py  # Operações de arquivo
│   │   ├── lsp_client.py    # Cliente LSP (Pyright)
│   │   ├── autocomplete.py  # Engine de autocompletar
│   │   ├── session.py       # Persistência de sessões
│   │   ├── tab_manager.py   # Gerenciamento de abas
│   │   └── theme_manager.py # Sistema de temas
│   ├── core_plugin/         # Plugins essenciais
│   │   ├── git_plugin.py    # Integração Git
│   │   ├── markdown_viewer.py
│   │   ├── python_syntax.py
│   │   ├── tagpoints_plugin.py
│   │   └── terminal_plugin.py
│   ├── events.py            # Sistema de eventos
│   └── interfaces.py        # Protocolos (contratos)
│
├── ui/                      # Interface Gráfica (GUI)
│   ├── window.py            # Janela principal
│   ├── editor_area.py       # Área de edição
│   ├── sidebar.py           # Explorador de arquivos
│   ├── status_bar.py        # Barra de status
│   ├── tab_bridge.py        # Ponte para abas
│   ├── control_panel.py     # Painel de configurações
│   ├── quick_access.py      # Projetos recentes
│   ├── shortcuts.py         # Gerenciador de atalhos
│   ├── welcome_dev!.py      # Tela de boas-vindas
│   ├── window_help.py       # Janela de ajuda
│   ├── estilo/              # Temas JSON
│   └── preferencias/        # Configurações
│
├── tui/                     # Interface de Terminal (TUI)
│   ├── window.py
│   ├── editor_area.py
│   ├── sidebar.py
│   ├── status_bar.py
│   └── shortcuts.py
│
├── plugins/                 # Plugins externos
│   ├── auto_close.py        # Auto-fechamento de pares
│   ├── color_preview.py     # Preview de cores
│   ├── image_viewer.py      # Visualizador de imagens
│   └── video_player.py      # Player de vídeo
│
├── docs/                    # Documentação
│   ├── README.md            # Este arquivo
│   ├── arquitetura.md       # Detalhes técnicos
│   ├── plugin_guide.md      # Guia de desenvolvimento
│   └── user_guide.md        # Manual do usuário
│
├── midia/                   # Recursos visuais
│   ├── imgs/
│   └── icon/
│
├── main.py                  # Ponto de entrada GUI
├── main_tui.py              # Ponto de entrada TUI
└── notohiis.sh              # Script de instalação/execução
```

### Princípios de Design

#### 1. Separação de Responsabilidades (SRP)
Cada classe tem uma única responsabilidade:
- `FileManager`: Apenas operações de arquivo
- `BufferManager`: Apenas leitura/escrita de conteúdo
- `LSPClient`: Apenas comunicação LSP
- `AppContext`: Apenas compartilhamento de estado

#### 2. Inversão de Dependência (DIP)
- Interfaces definidas em `core/interfaces.py`
- UI e TUI implementam os mesmos protocolos
- Core não conhece detalhes de implementação da UI

#### 3. Arquitetura em Camadas

```
┌─────────────────────────────────┐
│   UI/TUI (Apresentação)         │
├─────────────────────────────────┤
│   Plugins (Extensões)           │
├─────────────────────────────────┤
│   Core (Lógica de Negócio)     │
├─────────────────────────────────┤
│   Sistema de Arquivos / LSP    │
└─────────────────────────────────┘
```

### Fluxo de Dados

```
Usuário digita
    ↓
EditorArea captura evento
    ↓
AppContext.handle_typing()
    ↓
AutocompleteEngine.request_completion()
    ↓
LSPClient envia JSON-RPC (async)
    ↓
Callback atualiza UI (thread-safe)
```

---

## 🔌 Sistema de Plugins

### Tipos de Plugins

#### Core Plugins (Embutidos)
Localizados em `core/core_plugin/`, são carregados automaticamente:

1. **GitPlugin**: Integração Git completa
2. **MarkdownPlugin**: Preview de Markdown
3. **PythonSyntaxPlugin**: Realce de sintaxe Python
4. **TagPointsPlugin**: Sistema de marcadores

#### External Plugins (Dinâmicos)
Localizados em `plugins/`, carregados via `importlib`:

1. **AutoClosePlugin**: Auto-fechamento inteligente
2. **ColorPreviewPlugin**: Preview inline de cores
3. **ImageViewerPlugin**: Visualizador de imagens
4. **VideoPlayerPlugin**: Player de vídeo

### Criando um Plugin

#### Estrutura Básica

```python
# plugins/meu_plugin.py
from core.src.app_context import AppContext

class MeuPlugin:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self._setup()
    
    def _setup(self):
        """Inicialização do plugin"""
        if self.ctx.editor:
            self.ctx.editor.bind_key("<Control-p>", self.minha_acao)
    
    def minha_acao(self, event):
        """Ação customizada"""
        print("Plugin executado!")
        return "break"  # Previne propagação do evento
    
    def run(self):
        """Chamado a cada modificação no editor"""
        pass

def setup(ctx: AppContext):
    """Ponto de entrada obrigatório"""
    plugin = MeuPlugin(ctx)
    ctx.external_plugins.append(plugin)
```

#### Acessando Componentes

```python
# Editor
editor = self.ctx.editor
texto = editor.get_text()
editor.insert("Olá mundo!", "1.0")

# Sidebar
sidebar = self.ctx.sidebar
sidebar.refresh_explorer()

# Status Bar
status = self.ctx.status_bar
status.update_status(10, 5, "arquivo.py")

# Tema
tema = self.ctx.theme
cor_fundo = tema.get("editor", {}).get("bg", "#1e1e1e")
```

#### Exemplo: Plugin de Contador de Palavras

```python
# plugins/word_counter.py
import customtkinter as ctk
from core.src.app_context import AppContext

class WordCounterPlugin:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.label = None
        self._inject_ui()
    
    def _inject_ui(self):
        """Adiciona label na status bar"""
        if self.ctx.status_bar:
            self.label = ctk.CTkLabel(
                self.ctx.status_bar,
                text="0 palavras",
                font=("Segoe UI", 10)
            )
            self.label.pack(side="right", padx=10)
    
    def run(self):
        """Atualiza contagem a cada modificação"""
        if not self.ctx.editor or not self.label:
            return
        
        texto = self.ctx.editor.get_text()
        palavras = len(texto.split())
        self.label.configure(text=f"{palavras} palavras")

def setup(ctx: AppContext):
    plugin = WordCounterPlugin(ctx)
    ctx.external_plugins.append(plugin)
```

### API de Plugins

#### Interface TextEditor

```python
# Métodos disponíveis via ctx.editor
insert(text: str, index: str = "insert") -> None
delete(start: str, end: str = None) -> None
get_text(start: str = "1.0", end: str = "end") -> str
set_text(text: str) -> None
get_cursor_index() -> str
set_cursor(index: str) -> None
get_selection_range() -> Optional[Tuple[str, str]]
bind_key(key: str, callback: Callable) -> None
apply_tag(tag_name: str, start: str, end: str) -> None
configure_tag(tag_name: str, **kwargs) -> None
undo() -> None
redo() -> None
```

#### AppContext (Singleton)

```python
ctx = AppContext()

# Componentes
ctx.editor          # TextEditor
ctx.sidebar         # Sidebar
ctx.status_bar      # StatusBar
ctx.window          # MainWindow
ctx.tab_manager     # TabManager

# Estado
ctx.current_file    # str
ctx.project_root    # str
ctx.is_dirty        # bool
ctx.theme           # dict

# Plugins
ctx.py_plugin       # PythonSyntaxPlugin
ctx.git_plugin      # GitPlugin
ctx.md_plugin       # MarkdownPlugin
ctx.external_plugins  # List[Plugin]
```

---

## ⌨️ Atalhos de Teclado

### Gerais
| Atalho | Ação |
|--------|------|
| `Ctrl+N` | Novo arquivo/aba |
| `Ctrl+S` | Salvar arquivo |
| `Ctrl+O` | Abrir pasta |
| `Ctrl+R` | Projetos recentes |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+A` | Selecionar tudo |
| `F1` | Ajuda |
| `Ctrl+Alt+C` | Painel de controle |
| `Esc` | Fechar diálogos |

### Navegação
| Atalho | Ação |
|--------|------|
| `Alt+↑ + Número` | Mover N linhas para cima |
| `Alt+↓ + Número` | Mover N linhas para baixo |
| `Ctrl+Alt+↑` | Tag point anterior |
| `Ctrl+Alt+↓` | Próximo tag point |

### Edição
| Atalho | Ação |
|--------|------|
| `Ctrl+Z` | Desfazer |
| `Ctrl+Y` | Refazer |
| `Ctrl+Tab` | Forçar autocompletar |
| `Tab` | Aceitar sugestão |
| `Esc` | Fechar popup |

### Plugins
| Atalho | Ação |
|--------|------|
| `Ctrl+M` | Toggle Markdown preview |
| `Ctrl+G` | Git quick commit |

### Autocompletar
| Tecla | Ação |
|-------|------|
| `↓` ou `n` | Próxima sugestão |
| `↑` ou `p` | Sugestão anterior |
| `Enter` ou `Tab` | Aceitar |
| `Esc` | Cancelar |

---

## 🎨 Temas e Personalização

### Estrutura de Tema

Temas são arquivos JSON em `ui/estilo/`:

```json
{
  "editor": {
    "bg": "#1e1e1e",
    "fg": "#d4d4d4",
    "cursor": "#ffffff",
    "selection_bg": "#264f78",
    "gutter_bg": "#1e1e1e",
    "gutter_fg": "#858585"
  },
  "syntax": {
    "keyword": "#c678dd",
    "string": "#ce9178",
    "comment": "#5c6370",
    "number": "#d19a66",
    "builtin": "#56b6c2",
    "definition": "#61afef"
  },
  "sidebar": {
    "bg": "#21252b",
    "fg": "#abb2bf",
    "hover": "#2c313a",
    "label": "#5c6370"
  },
  "status_bar": {
    "bg": "#21252b",
    "fg": "#9da5b4",
    "hover": "#2c313a"
  }
}
```

### Aplicando Temas

**Via Interface:**
1. `Ctrl+Alt+C` → Painel de Controle
2. Aba "Aparência"
3. Selecione o tema
4. Clique em "Aplicar" ou `Ctrl+S`

**Via Código:**
```python
from core.src.theme_manager import ThemeManager

# Listar temas disponíveis
temas = ThemeManager.get_theme_display_list()

# Carregar tema
tema = ThemeManager.load_theme("onedark")

# Aplicar na janela
window.apply_theme("onedark")
```

### Criando Tema Personalizado

1. Copie um tema existente de `ui/estilo/`
2. Renomeie para `meu_tema.json`
3. Edite as cores
4. Reinicie o editor
5. Selecione no painel de controle

---

## ❓ FAQ

### Como instalar dependências opcionais?

```bash
# Para suporte completo a imagens (SVG)
pip install svglib reportlab

# Para reprodução de vídeo
pip install opencv-python

# Para Markdown avançado
pip install markdown2 tkinterweb
```

### Como desabilitar o ocultamento inteligente de abas?

1. `Ctrl+Alt+C` → Painel de Controle
2. Desmarque "Ocultamento inteligente de abas"
3. As abas ficarão sempre visíveis

### Como usar o editor via SSH?

```bash
# No servidor remoto
ntht arquivo.py
```

A interface TUI funciona perfeitamente via SSH/Tmux.

### Como contribuir com plugins?

1. Crie seu plugin em `plugins/meu_plugin.py`
2. Implemente a função `setup(ctx)`
3. Teste localmente
4. Envie um Pull Request no GitHub

### O autocompletar não funciona

Verifique se o Pyright está instalado:
```bash
pip install pyright
```

O LSP é iniciado automaticamente ao abrir o editor.

### Como limpar o cache de sessões?

```bash
rm -rf core/cacheuser/
```

Isso remove sessões salvas e tag points.

---

## 📝 Licença

Notohiis é licenciado sob **GPL-3.0**. Veja o arquivo `LICENSE` para detalhes.

---

## 👨‍💻 Autor

**John BrenoF**

- GitHub: [John-BrenoF](https://github.com/John-BrenoF)
- Email: johnbrenosf7@proton.me

---

## 🙏 Agradecimentos

- **CustomTkinter**: Framework de UI moderna
- **Textual**: Framework TUI poderoso
- **Pyright**: Servidor LSP para Python

---

**Versão da Documentação**: 0.4-alpha (Batata estilosa) 🥔😎
