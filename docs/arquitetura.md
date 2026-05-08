# Documentação Técnica - Notohiis Editor

O Notohiis é um editor de texto modular desenvolvido em Python, projetado para suportar múltiplas interfaces (Gráfica via CustomTkinter e Terminal via Textual) compartilhando o mesmo núcleo lógico.

## 1. Arquitetura Geral

A aplicação é dividida em três camadas principais:

*   **Core (Coração):** Contém a lógica de processamento, manipulação de arquivos, gerenciamento de sessão e comunicação com servidores de linguagem (LSP). É agnóstico de interface.
*   **UI/TUI (Interface):** Camadas de apresentação. A `ui/` utiliza CustomTkinter para uma experiência desktop moderna, enquanto a `tui/` utiliza Textual para uso em terminal.
*   **Plugins:** Extensões que adicionam funcionalidades específicas (Git, Markdown, Sintaxe) sem alterar o código base do motor.

## 2. O Princípio de Responsabilidade Única (SRP)

O projeto aplica o SRP rigorosamente para evitar "God Objects" (objetos que fazem tudo). Cada classe no diretório `core/src/` tem um único propósito:

*   **`FileManager`**: Responsável exclusivamente por interagir com o sistema de arquivos (listar diretórios, criar e deletar caminhos).
*   **`BufferManager`**: Gerencia apenas a leitura e escrita de conteúdo de texto, tratando codificações (UTF-8) e erros de I/O.
*   **`LSPClient`**: Lida apenas com o protocolo JSON-RPC para comunicação com servidores de linguagem (como Pyright). Não sabe o que é um editor ou um botão.
*   **`SessionManager`**: Foca apenas na persistência do estado da aplicação (último projeto aberto).
*   **`AppContext`**: Atua como um Singleton para compartilhamento de estado global, servindo de ponte de comunicação entre componentes sem acoplamento direto.

## 3. Fluxo de Funcionamento

### Inicialização
1. O `main.py` configura o ambiente e o `AppContext`.
2. O `AutocompleteEngine` é instanciado, tentando iniciar o servidor LSP em background.
3. Plugins core (Git, Markdown, Sintaxe) são carregados dinamicamente.
4. A interface escolhida (MainWindow ou TuiWindow) é renderizada.

### Ciclo de Edição e Autocomplete
1. O usuário digita no `EditorArea`.
2. A interface captura o evento e notifica o `AutocompleteEngine` via `notify_change`.
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
├── docs/               # Documentação e Guias
└── plugins/            # Espaço para plugins da comunidade
```

---
*Notohiis - Versão 0.1-alpha*
