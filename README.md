<p align="center">
  <img src="midia/icon/nth.png" width="200" alt="Notohiis Logo">
</p>

# 🖊️ Notohiis Editor

**Simples por padrão. Personalizado quando necessário.**

O Notohiis é um editor de texto minimalista e modular desenvolvido em Python. Ele foi projetado para quem busca um ambiente de escrita e codificação limpo, mas não abre mão de "turbinar" suas ferramentas com funcionalidades avançadas através de um sistema de plugins flexível.

---

## 🚀 A Filosofia

O Notohiis segue o princípio de que o editor deve sair do seu caminho para que você possa focar no que importa. 

- **Minimalismo:** Uma interface focada no conteúdo, sem distrações desnecessárias.
- **Modularidade:** O núcleo (core) é separado da interface. Use no Desktop (GUI) ou no Terminal (TUI).
- **Extensibilidade:** Se você precisa de uma função que não existe, basta criar um plugin em Python. O editor se adapta ao seu fluxo de trabalho, e não o contrário.

## ✨ Funcionalidades Core

- 🎨 **Tematização Total:** Controle cores e estilos via arquivos JSON simples.
- 🔌 **Arquitetura de Plugins:** Carregamento dinâmico de extensões (Git, Markdown, Auto-close, etc).
- 🌐 **Híbrido:** Mesma lógica para interfaces gráficas (CustomTkinter) e terminal (Textual).
- 🛠️ **Focado no Dev:** Integração Git nativa e suporte a múltiplas linguagens.

## 🛠️ Como Iniciar

O Notohiis vem com um automatizador que cuida de tudo para você. Basta clonar e executar:

```bash
chmod +x notohiis.sh
./notohiis.sh
```

*Dica: Na primeira execução, o script criará um alias `nth` para que você possa abrir o editor de qualquer lugar do terminal.*

## 🧩 Turbinando com Plugins

Personalizar o Notohiis é tão simples quanto escrever um script Python. Coloque seus plugins na pasta `/plugins` e eles serão carregados automaticamente.

Exemplo de como o Notohiis pode ser expandido:
- **Auto-close:** Fecha parênteses e aspas automaticamente.
- **Color Preview:** Visualiza cores hexadecimais diretamente no código.
- **Git Integration:** Acompanhe o status do seu repositório na barra de status e na barra lateral.

## 📂 Estrutura do Projeto

```text
├── core/           # O coração do editor (Lógica e SRP)
├── ui/             # Interface Gráfica moderna
├── tui/            # Interface de Terminal clássica
├── plugins/        # Sua oficina de personalização
└── notohiis.sh     # O ponto de entrada inteligente
```

---
*Notohiis - Versão 0.2-alpha*  
*"frango  com batata doce" Edition*

Desenvolvido com ❤️ e Python.
