# Notohiis Editor - Guia Completo

![Versão](https://img.shields.io/badge/versão-0.4--alpha-blue)
![Licença](https://img.shields.io/badge/licença-LUMEJ--3.0-green)
![Python](https://img.shields.io/badge/python-3.8+-yellow)

**Notohiis** é um editor de texto moderno, extensível e leve, desenvolvido em Python com suporte para interface gráfica (GUI) e terminal (TUI). Projetado para desenvolvedores que buscam simplicidade sem abrir mão de recursos avançados.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Instalação](#instalação)
3. [Recursos Principais](#recursos-principais)
4. [Guia de Uso](#guia-de-uso)
5. [Atalhos de Teclado](#atalhos-de-teclado)
6. [Plugins](#plugins)
7. [Temas](#temas)
8. [FAQ](#faq)

---

## 🎯 Visão Geral

### Características Principais

#### Interface Dupla
- **GUI (CustomTkinter)**: Interface gráfica moderna e responsiva
- **TUI (Textual)**: Interface de terminal para uso remoto via SSH

#### Recursos de Edição
- ✅ **Realce de Sintaxe Python**: Coloração inteligente de código
- ✅ **Autocompletar com LSP**: Integração com Pyright + fallback local
- ✅ **Navegação Rápida**: Alt+↑/↓ + Número (1-9) para mover cursor
- ✅ **Auto-fechamento**: Parênteses, colchetes, chaves e aspas
- ✅ **Undo/Redo Granular**: Controle atômico de transações
- ✅ **Numeração de Linhas**: Com margem Git integrada

#### Gerenciamento de Arquivos
- 📁 **Explorador Lateral**: Navegação em árvore com ícones
- 📂 **Projetos Recentes**: Acesso rápido (Ctrl+R)
- 🔖 **Sistema de Abas**: Multi-arquivo com ocultamento inteligente
- 💾 **Sessões Persistentes**: Restaura último projeto

#### Integração Git
- 🔄 **Status em Tempo Real**: Indicadores [M], [A], [D]
- 📊 **Quick Commit**: Interface rápida (Ctrl+G)
- 🎨 **Decoração de Arquivos**: Cores por status

#### Visualizadores
- 📝 **Markdown Preview**: Renderização HTML
- 🖼️ **Image Viewer**: PNG, JPG, SVG com zoom/pan
- 🎬 **Video Player**: MP4, AVI, MKV com controles

---

## 📦 Instalação

### Requisitos
- Python 3.8+
- Git (opcional, para integração)
- Linux, macOS ou Windows

### Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/notohiis.git
cd notohiis

# Execute o instalador
chmod +x notohiis.sh
./notohiis.sh
```

O script `notohiis.sh`:
1. Cria ambiente virtual (`.venv/`)
2. Instala dependências
3. Configura alias `nth`

### Dependências

**Essenciais:**
```bash
pip install customtkinter textual Pillow
```

**Opcionais:**
```bash
# Markdown
pip install markdown2 tkinterweb

# Imagens SVG
pip install svglib reportlab

# Vídeo
pip install opencv-python

# LSP Python
pip install pyright
```

### Executando

```bash
# GUI
nth

# TUI
ntht

# Abrir arquivo
nth arquivo.py
ntht documento.md
```

---

## 🚀 Recursos Principais

### 1. Editor de Texto

#### Realce de Sintaxe
- Suporte nativo para Python
- Destaque de keywords, strings, comentários
- Cores configuráveis via temas

#### Autocompletar Inteligente
- **LSP (Pyright)**: Sugestões contextuais
- **Fallback Local**: Palavras-chave Python
- **Navegação**: ↑/↓ ou n/p
- **Aceitar**: Tab ou Enter

#### Navegação Rápida
```
Alt+↑ + 5  → Sobe 5 linhas
Alt+↓ + 3  → Desce 3 linhas
Esc        → Cancela modo navegação
```

### 2. Sistema de Abas

#### Recursos
- Múltiplos arquivos abertos
- Indicador de modificação (●)
- Ocultamento inteligente (hover)
- Botão + para nova aba

#### Configuração
```
Ctrl+Alt+C → Painel de Controle
→ Aparência
→ "Ocultamento inteligente de abas"
```

### 3. Integração Git

#### Status Visual
- **[M]** - Modificado (amarelo)
- **[A]** - Adicionado (verde)
- **[D]** - Deletado (vermelho)
- **[R]** - Renomeado (amarelo)

#### Quick Commit
```
Ctrl+G → Abre janela de commit
→ Mostra arquivos alterados
→ Digite mensagem
→ Enter para confirmar
```

### 4. Tag Points

#### Criar Marcador
```
Botão direito na linha → "Adicionar Tag Point"
→ Alias: nome do marcador
→ Descrição: nota breve
→ Cor: Vermelho/Verde/Azul/Amarelo
```

#### Navegar
```
Ctrl+Alt+↑  → Tag anterior
Ctrl+Alt+↓  → Próximo tag
```

### 5. Markdown Preview

#### Ativar
```
Abrir arquivo .md
→ Ctrl+M ou "View Mode"
→ Visualiza HTML renderizado
→ Ctrl+M para voltar
```

#### Recursos
- Renderização em tempo real
- Tema dinâmico (segue editor)
- Suporte a tabelas, código, blockquotes

### 6. Visualizadores de Mídia

#### Imagens
```
Abrir PNG/JPG/SVG
→ "Visualizar Imagem"
→ Scroll: zoom
→ Arrastar: pan
```

#### Vídeos
```
Abrir MP4/AVI/MKV
→ "Assistir Vídeo"
→ ▶/⏸: play/pause
→ Slider: busca
```

---

## ⌨️ Atalhos de Teclado

### Gerais
| Atalho | Ação |
|--------|------|
| `Ctrl+N` | Novo arquivo/aba |
| `Ctrl+S` | Salvar |
| `Ctrl+O` | Abrir pasta |
| `Ctrl+R` | Projetos recentes |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+A` | Selecionar tudo |
| `F1` | Ajuda |
| `Ctrl+Alt+C` | Painel de controle |

### Navegação
| Atalho | Ação |
|--------|------|
| `Alt+↑ + N` | N linhas acima |
| `Alt+↓ + N` | N linhas abaixo |
| `Ctrl+Alt+↑` | Tag anterior |
| `Ctrl+Alt+↓` | Próximo tag |

### Edição
| Atalho | Ação |
|--------|------|
| `Ctrl+Z` | Desfazer |
| `Ctrl+Y` | Refazer |
| `Ctrl+Tab` | Forçar autocompletar |

### Plugins
| Atalho | Ação |
|--------|------|
| `Ctrl+M` | Markdown preview |
| `Ctrl+G` | Git commit |

---

## 🔌 Plugins

### Core Plugins (Embutidos)

#### 1. GitPlugin
- Monitoramento de repositório
- Decoração de arquivos
- Quick commit

#### 2. PythonSyntaxPlugin
- Realce de sintaxe
- Detecção de keywords, strings, comentários
- Suporte a decoradores

#### 3. MarkdownPlugin
- Preview HTML
- Tema dinâmico
- Suporte a extensões

#### 4. TagPointsPlugin
- Marcadores de linha
- Navegação rápida
- Persistência em JSON

### External Plugins

#### 1. AutoClosePlugin
- Auto-fecha (), [], {}, "", ''
- Backspace inteligente
- Pular fechamento existente

#### 2. ColorPreviewPlugin
- Preview de cores hex, rgb, hsl
- Suporte a nomes CSS
- Color picker integrado

#### 3. ImageViewerPlugin
- Visualização de imagens
- Zoom e pan
- Suporte SVG

#### 4. VideoPlayerPlugin
- Reprodução de vídeo
- Controles de playback
- Busca (seek)

---

## 🎨 Temas

### Estrutura de Tema

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

### Aplicar Tema

```
Ctrl+Alt+C → Aparência
→ Selecionar tema
→ "Aplicar" ou Ctrl+S
```

### Criar Tema

1. Copiar tema de `ui/estilo/`
2. Renomear para `meu_tema.json`
3. Editar cores
4. Reiniciar editor
5. Selecionar no painel

---

## ❓ FAQ

### Como instalar dependências opcionais?

```bash
pip install svglib reportlab opencv-python markdown2 tkinterweb
```

### Como desabilitar ocultamento de abas?

```
Ctrl+Alt+C → Aparência
→ Desmarcar "Ocultamento inteligente"
```

### Como usar via SSH?

```bash
ntht arquivo.py
```

### Autocompletar não funciona?

```bash
pip install pyright
```

### Como limpar cache?

```bash
rm -rf core/cacheuser/
```

---

## 📝 Licença

LUMEJ

## 👨‍💻 Autor

**John BrenoF**

---

**Versão**: 0.4-alpha (Batata estilosa) 🥔😎

*Atualizado: 21/06/2026*
