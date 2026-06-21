# Arquitetura Técnica - Notohiis Editor

## 📐 Visão Geral da Arquitetura

O Notohiis é um editor de texto modular desenvolvido em Python, projetado com arquitetura em camadas que suporta múltiplas interfaces (GUI e TUI) compartilhando o mesmo núcleo lógico.

### Princípios Fundamentais

1. **Separação de Responsabilidades (SRP)**
2. **Inversão de Dependência (DIP)**
3. **Interface Segregation (ISP)**
4. **Arquitetura em Camadas**
5. **Event-Driven Design**

---

## 🏗️ Estrutura em Camadas

```
┌─────────────────────────────────────────┐
│  Camada de Apresentação (UI/TUI)        │
│  - window.py, editor_area.py            │
│  - Implementa protocolos do Core        │
├─────────────────────────────────────────┤
│  Camada de Plugins                      │
│  - Core Plugins (embutidos)             │
│  - External Plugins (dinâmicos)         │
├─────────────────────────────────────────┤
│  Camada de Lógica (Core)                │
│  - app_context.py (Singleton)           │
│  - Gerenciadores (Buffer, File, LSP)    │
│  - Engines (Autocomplete, Theme)        │
├─────────────────────────────────────────┤
│  Camada de Infraestrutura               │
│  - Sistema de Arquivos                  │
│  - Processos LSP                        │
│  - Git CLI                              │
└─────────────────────────────────────────┘
```

---

## 📁 Estrutura de Diretórios Detalhada

```
notohiis/
├── core/                           # Núcleo do editor
│   ├── src/                        # Componentes principais
│   │   ├── app_context.py          # Singleton de estado global
│   │   ├── buffer.py               # BufferManager (I/O de texto)
│   │   ├── file_manager.py         # FileManager (operações FS)
│   │   ├── lsp_client.py           # LSPClient (JSON-RPC)
│   │   ├── autocomplete.py         # AutocompleteEngine
│   │   ├── session.py              # SessionManager (persistência)
│   │   ├── tab_manager.py          # TabManager (abas)
│   │   └── theme_manager.py        # ThemeManager (temas)
│   │
│   ├── core_plugin/                # Plugins essenciais
│   │   ├── git_plugin.py           # Integração Git
│   │   ├── markdown_viewer.py      # Preview Markdown
│   │   ├── python_syntax.py        # Realce Python
│   │   ├── tagpoints_plugin.py     # Marcadores de linha
│   │   └── terminal_plugin.py      # Terminal integrado
│   │
│   ├── events.py                   # Sistema de eventos
│   ├── interfaces.py               # Protocolos (contratos)
│   └── cacheuser/                  # Cache de sessões/tags
│
├── ui/                             # Interface Gráfica
│   ├── window.py                   # MainWindow (janela principal)
│   ├── editor_area.py              # EditorArea (TextEditor)
│   ├── sidebar.py                  # Sidebar (explorador)
│   ├── status_bar.py               # StatusBar (barra inferior)
│   ├── tab_bridge.py               # TabBridge (gerenciador UI)
│   ├── control_panel.py            # ControlPanel (configurações)
│   ├── quick_access.py             # QuickAccess (projetos)
│   ├── shortcuts.py                # ShortcutManager
│   ├── welcome_dev!.py             # WelcomeWindow
│   ├── window_help.py              # HelpWindow
│   ├── estilo/                     # Temas JSON
│   └── preferencias/               # Configurações
│
├── tui/                            # Interface Terminal
│   ├── window.py                   # TuiWindow (Textual App)
│   ├── editor_area.py              # EditorArea (TextArea)
│   ├── sidebar.py                  # Sidebar (DirectoryTree)
│   ├── status_bar.py               # StatusBar (Footer)
│   └── shortcuts.py                # ShortcutManager
│
├── plugins/                        # Plugins externos
│   ├── __init__.py
│   ├── auto_close.py               # Auto-fechamento
│   ├── color_preview.py            # Preview de cores
│   ├── image_viewer.py             # Visualizador de imagens
│   └── video_player.py             # Player de vídeo
│
├── docs/                           # Documentação
│   ├── GUIA_COMPLETO.md            # Guia do usuário
│   ├── arquitetura.md              # Este arquivo
│   ├── PLUGIN_DEV.md               # Guia de plugins
│   └── REFERENCIA_TECNICA.md       # API Reference
│
├── midia/                          # Recursos visuais
│   ├── imgs/
│   └── icon/
│
├── main.py                         # Entry point GUI
├── main_tui.py                     # Entry point TUI
└── notohiis.sh                     # Script de instalação
```

---

## 🔧 Componentes do Core

### 1. AppContext (Singleton)

**Responsabilidade**: Compartilhamento de estado global entre componentes.

```python
class AppContext:
    _instance = None
    
    # Componentes UI
    window: Optional[AppWindow]
    editor: Optional[TextEditor]
    sidebar: Optional[Sidebar]
    status_bar: Optional[StatusBar]
    tab_manager: Optional[TabManager]
    tab_bridge: Optional[TabBridge]
    
    # Estado
    current_file: Optional[str]
    project_root: Optional[str]
    is_dirty: bool
    theme: Dict[str, Any]
    selected_theme: str
    
    # Plugins
    py_plugin: Optional[PythonSyntaxPlugin]
    git_plugin: Optional[GitPlugin]
    md_plugin: Optional[MarkdownPlugin]
    external_plugins: List[Any]
    
    # Engines
    autocomplete_engine: Optional[AutocompleteEngine]
```

**Padrão**: Singleton com `__new__`

### 2. BufferManager

**Responsabilidade**: Leitura e escrita de arquivos de texto.

```python
class BufferManager:
    @staticmethod
    def read_file(path: str) -> str:
        """Lê arquivo com encoding UTF-8"""
        
    @staticmethod
    def save_file(path: str, content: str) -> bool:
        """Salva arquivo com tratamento de erros"""
```

**Características**:
- Encoding UTF-8 padrão
- Tratamento de erros de I/O
- Métodos estáticos (stateless)

### 3. FileManager

**Responsabilidade**: Operações no sistema de arquivos.

```python
class FileManager:
    @staticmethod
    def list_directory(path: str) -> List[Dict]:
        """Lista arquivos e diretórios"""
        
    @staticmethod
    def create_file(path: str) -> bool:
        """Cria arquivo vazio"""
        
    @staticmethod
    def create_directory(path: str) -> bool:
        """Cria diretório"""
        
    @staticmethod
    def delete_path(path: str) -> bool:
        """Deleta arquivo ou diretório"""
        
    @staticmethod
    def rename_path(old: str, new_name: str) -> bool:
        """Renomeia arquivo/diretório"""
```

### 4. LSPClient

**Responsabilidade**: Comunicação com Language Server Protocol.

```python
class LSPClient:
    def __init__(self, server_cmd: List[str]):
        self.process: subprocess.Popen
        self.request_id: int
        
    def send_request(self, method: str, params: Dict) -> int:
        """Envia requisição JSON-RPC"""
        
    def send_notification(self, method: str, params: Dict):
        """Envia notificação (sem resposta)"""
        
    def _reader_thread(self):
        """Thread para ler respostas do servidor"""
```

**Características**:
- Comunicação assíncrona
- Thread dedicada para leitura
- Callbacks para respostas

### 5. AutocompleteEngine

**Responsabilidade**: Orquestração de sugestões de código.

```python
class AutocompleteEngine:
    def __init__(self):
        self.lsp_client: Optional[LSPClient]
        self.fallback_keywords: List[str]
        
    def request_completion(
        self, 
        line: int, 
        col: int, 
        callback: Callable
    ):
        """Solicita sugestões (LSP ou fallback)"""
```

**Estratégia**:
1. Tenta LSP primeiro
2. Fallback para keywords locais
3. Callback thread-safe para UI

### 6. SessionManager

**Responsabilidade**: Persistência de sessões e configurações.

```python
class SessionManager:
    @staticmethod
    def save_session(project_root: str):
        """Salva sessão atual"""
        
    @staticmethod
    def load_session() -> Optional[str]:
        """Carrega última sessão"""
        
    @staticmethod
    def get_recent_projects() -> List[str]:
        """Lista projetos recentes"""
        
    @staticmethod
    def save_theme_pref(theme_name: str):
        """Salva tema preferido"""
```

**Armazenamento**: JSON em `core/cacheuser/`

### 7. TabManager

**Responsabilidade**: Gerenciamento de abas (buffers múltiplos).

```python
@dataclass
class Tab:
    id: int
    title: str
    path: Optional[str]
    content: str
    is_dirty: bool
    
class TabManager:
    def create_tab(self) -> Tab:
        """Cria nova aba"""
        
    def open_file(self, path: str) -> Tab:
        """Abre arquivo em nova aba"""
        
    def close_tab(self, tab_id: int, force: bool) -> bool:
        """Fecha aba"""
        
    def select_tab(self, tab_id: int) -> Optional[Tab]:
        """Ativa aba"""
```

### 8. ThemeManager

**Responsabilidade**: Carregamento e gerenciamento de temas.

```python
class ThemeManager:
    @staticmethod
    def load_theme(name: str) -> Dict:
        """Carrega tema JSON"""
        
    @staticmethod
    def get_theme_display_list() -> List[str]:
        """Lista temas disponíveis"""
        
    @staticmethod
    def resolve_theme_path(name: str) -> str:
        """Resolve caminho do tema"""
```

---

## 🔌 Sistema de Protocolos (Interfaces)

### TextEditor Protocol

```python
class TextEditor(Protocol):
    # Manipulação de texto
    def insert(self, text: str, index: str = "insert") -> None: ...
    def delete(self, start: str, end: Optional[str] = None) -> None: ...
    def set_text(self, text: str) -> None: ...
    def get_text(self, start: str = "1.0", end: str = "end") -> str: ...
    
    # Cursor e seleção
    def get_cursor_index(self) -> str: ...
    def set_cursor(self, index: str) -> None: ...
    def get_selection_range(self) -> Optional[Tuple[str, str]]: ...
    
    # Eventos
    def bind_key(self, key: str, callback: Callable) -> None: ...
    
    # Tags (sintaxe)
    def apply_tag(self, tag_name: str, start: str, end: str) -> None: ...
    def configure_tag(self, tag_name: str, **kwargs) -> None: ...
    
    # Undo/Redo
    def undo() -> None: ...
    def redo() -> None: ...
    def begin_undo_group() -> None: ...
    def end_undo_group() -> None: ...
```

**Implementações**:
- `ui/editor_area.py`: EditorArea (CustomTkinter)
- `tui/editor_area.py`: EditorArea (Textual)

### Outros Protocolos

```python
class StatusBar(Protocol):
    def update_status(self, line: int, column: int, file_path: str) -> None: ...
    def update_git_ui(self, status_text: str, is_dirty: bool) -> None: ...

class Sidebar(Protocol):
    def refresh_explorer(self) -> None: ...
    @property
    def item_widgets(self) -> dict: ...

class AppWindow(Protocol):
    def after(self, ms: int, func: Callable) -> None: ...
    def destroy(self) -> None: ...
    def bind(self, sequence: str, func: Callable) -> None: ...
```

---

## 🔄 Fluxos de Dados

### Fluxo de Inicialização

```
1. notohiis.sh
   ↓
2. Ativa .venv/
   ↓
3. main.py
   ↓
4. AppContext.__new__() (Singleton)
   ↓
5. AutocompleteEngine (inicia LSP)
   ↓
6. MainWindow (cria UI)
   ↓
7. Carrega Core Plugins
   ↓
8. Carrega External Plugins (importlib)
   ↓
9. SessionManager.load_session()
   ↓
10. Renderiza interface
```

### Fluxo de Autocompletar

```
Usuário digita
    ↓
EditorArea._trigger_autocomplete()
    ↓
AppContext.autocomplete_engine.request_completion()
    ↓
LSPClient.send_request("textDocument/completion")
    ↓
[Thread LSP] Aguarda resposta
    ↓
Callback com sugestões
    ↓
editor.after(0, lambda: _update_popup_safe())
    ↓
Popup renderizado (thread-safe)
```

### Fluxo de Git Status

```
Arquivo salvo
    ↓
StatusBar.update_status()
    ↓
GitPlugin.async_update_status()
    ↓
[Thread] subprocess.run(["git", "status"])
    ↓
GitPlugin.get_status_data()
    ↓
window.after(0, lambda: decorate_sidebar())
    ↓
Sidebar atualizada com cores
```

---

## 🎯 Padrões de Design Utilizados

### 1. Singleton
- **AppContext**: Estado global único

### 2. Protocol (Duck Typing)
- **TextEditor, StatusBar, Sidebar**: Contratos de interface

### 3. Strategy
- **AutocompleteEngine**: LSP vs Fallback

### 4. Observer (Event-Driven)
- **EventBus**: Sistema de eventos pub/sub

### 5. Factory
- **ThemeManager**: Criação de temas

### 6. Bridge
- **TabBridge**: Ponte entre TabManager e UI

---

## 🧵 Gerenciamento de Threads

### Threads Ativas

1. **Main Thread (Tkinter/Textual)**
   - Renderização de UI
   - Event loop

2. **LSP Reader Thread**
   - Leitura de respostas do servidor
   - Parsing JSON-RPC

3. **Git Status Thread**
   - Execução de comandos Git
   - Parsing de output

4. **Video Decoder Thread** (plugin)
   - Decodificação de frames
   - Queue de frames

### Thread Safety

```python
# Atualização de UI sempre via after()
def callback_from_thread(data):
    ctx.window.after(0, lambda: update_ui_safe(data))
```

---

## 📊 Diagrama de Dependências

```
main.py
  ├─> AppContext (singleton)
  ├─> MainWindow
  │     ├─> EditorArea (implements TextEditor)
  │     ├─> Sidebar (implements Sidebar)
  │     ├─> StatusBar (implements StatusBar)
  │     └─> TabBridge
  │           └─> TabManager
  ├─> AutocompleteEngine
  │     └─> LSPClient
  ├─> Core Plugins
  │     ├─> GitPlugin
  │     ├─> PythonSyntaxPlugin
  │     ├─> MarkdownPlugin
  │     └─> TagPointsPlugin
  └─> External Plugins (dynamic)
        ├─> AutoClosePlugin
        ├─> ColorPreviewPlugin
        ├─> ImageViewerPlugin
        └─> VideoPlayerPlugin
```

---

## 🔒 Regras de Arquitetura

### 1. Isolamento de Camadas
- **Core** não conhece **UI/TUI**
- **UI/TUI** implementam protocolos do **Core**
- **Plugins** acessam via **AppContext**

### 2. Comunicação
- **Síncrona**: Métodos diretos
- **Assíncrona**: Threads + callbacks
- **Event-Driven**: EventBus (futuro)

### 3. Tematização
- Cores sempre via `theme.get("section", {}).get("key")`
- Nunca hardcoded

### 4. Persistência
- JSON para configurações
- Cache em `core/cacheuser/`
- `.gitignore` automático

---

## 🚀 Performance

### Otimizações Implementadas

1. **Debouncing**: Color preview (350ms)
2. **Lazy Loading**: Plugins externos
3. **Caching**: Temas, sessões
4. **Async I/O**: Git, LSP
5. **Bisect Search**: Syntax highlighting (line offsets)

---

## 📝 Notas de Implementação

### Compatibilidade Wayland
- Centralização de janelas via `screen_width/height`
- `transient()` para diálogos
- `resizable(False, False)` para popups

### Scroll Universal
- Suporte a `event.num` (Linux) e `event.delta` (Win/Mac)
- Fallback manual para `_parent_canvas`

### Undo/Redo Atômico
- `autoseparators=False` no Tkinter Text
- `begin_undo_group()` / `end_undo_group()`
- `edit_separator()` manual

---

**Versão da Arquitetura**: 0.4-alpha

*Última atualização: 21/06/2026*
