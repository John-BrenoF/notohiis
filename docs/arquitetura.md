# Documentação Técnica - Notohiis Editor

O Notohiis é um editor de texto modular desenvolvido em Python, projetado para suportar múltiplas interfaces (Gráfica via CustomTkinter e Terminal via Textual) compartilhando o mesmo núcleo lógico.

## 1. Arquitetura Geral

A aplicação é dividida em três camadas principais:

*   **Core (Coração):** Contém a lógica de processamento, manipulação de arquivos, gerenciamento de sessão e comunicação com servidores de linguagem (LSP). É agnóstico de interface.
*   **UI/TUI (Interface):** Camadas de apresentação. A `ui/` utiliza CustomTkinter para uma experiência desktop moderna, enquanto a `tui/` utiliza Textual para uso em terminal.
*   **Plugins:** Divididos em **Core Plugins** (embutidos e essenciais) e **External Plugins** (carregados dinamicamente da pasta `plugins/`).

## 2. O Princípio de Responsabilidade Única (SRP)

O projeto aplica o SRP rigorosamente para evitar "God Objects" (objetos que fazem tudo). Cada classe no diretório `core/src/` tem um único propósito:

*   **`notohiis.sh`**: Gerencia o ambiente virtual (VENV), dependências Python e o alias `nth`.
*   **`FileManager`**: Responsável exclusivamente por interagir com o sistema de arquivos (listar diretórios, criar e deletar caminhos).
*   **`BufferManager`**: Gerencia apenas a leitura e escrita de conteúdo de texto, tratando codificações (UTF-8) e erros de I/O.
*   **`LSPClient`**: Lida apenas com o protocolo JSON-RPC para comunicação com servidores de linguagem (como Pyright). Não sabe o que é um editor ou um botão.
*   **`AutocompleteEngine`**: Orquestra as sugestões, alternando entre o servidor LSP e o fallback de palavras-chave locais.
*   **`AppContext`**: Atua como um Singleton para compartilhamento de estado global, servindo de ponte de comunicação entre componentes sem acoplamento direto.

## 3. Fluxo de Funcionamento

### Inicialização
1. O usuário executa `notohiis.sh` (ou o alias `nth`).
2. O script garante que o ambiente virtual está ativo e as dependências (`customtkinter`, `markdown2`, etc.) instaladas.
3. O `main.py` inicializa o `AppContext` e o `AutocompleteEngine` (disparando o `pyright-langserver`).
4. **Plugins Core** são importados explicitamente.
5. A `MainWindow` é criada.
6. **Plugins Externos** são carregados via `importlib` a partir da pasta `plugins/`, chamando a função `setup(ctx)`.
7. Se um arquivo foi passado via CLI, ele é carregado no buffer principal.

### Ciclo de Edição e Eventos
1. O usuário digita no `EditorArea`.
2. O `GitPlugin` monitora mudanças no repositório de forma assíncrona, decorando a Sidebar com cores e ícones ([M], [A], [D]).
3. A interface captura eventos de teclas para o `AutocompleteEngine`.
3. O `LSPClient` envia uma notificação assíncrona ao servidor (ex: Pyright).
4. Quando o servidor responde, um callback é disparado para atualizar o popup de sugestões na UI, sem travar a digitação do usuário.

## 4. Regras de Design

1.  **Isolamento da Lógica**: Nenhuma lógica de manipulação de arquivos ou Git deve ser escrita diretamente nos arquivos da `ui/`. Utilize sempre os métodos do `core/`.
2.  **Comunicação via Contexto**: Para acessar o editor a partir de um plugin, utilize `AppContext().editor_container`. Isso permite que o plugin funcione tanto na UI quanto na TUI.
3.  **Tematização**: Cores e estilos devem ser lidos do `ui/estilo/editor.json`. Nunca utilize cores "hardcoded" (fixas) nos widgets.
4.  **Assincronismo**: Operações pesadas (Git, LSP, leitura de diretórios grandes) devem ser executadas em threads separadas para manter a interface responsiva.

## 5. Estrutura de Pastas

```text
├── core/
│   ├── core_plugin/    # Plugins internos (Git, Markdown, Syntax)
│   └── src/            # O motor do editor (SRP puro)
├── ui/                 # Interface Gráfica (CustomTkinter)
├── tui/                # Interface de Terminal (Textual)
├── .venv/              # Ambiente virtual isolado
├── docs/               # Documentação e Guias
└── plugins/            # Espaço para plugins da comunidade
```
