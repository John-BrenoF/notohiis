
<p align="center">
  <img src="midia/icon/nth.png" width="220" alt="Notohiis Logo">
</p>

<h1 align="center">🖊️ Notohiis Editor</h1>

<p align="center">
  <strong>Simples por padrão.<br>Extremamente poderoso quando você precisa.</strong>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-lumej-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Version-0.2--alpha-orange" alt="Version"></a>
</p>

---

**Notohiis** é um editor de texto minimalista, rápido e altamente modular, feito em Python. Projetado para quem valoriza foco, beleza e controle total sobre sua ferramenta de escrita e codificação.

---

## 🚀 Filosofia

O editor deve desaparecer para que **você** brilhe.

- **Minimalismo intencional** — Interface limpa, sem distrações.
- **Modularidade extrema** — Core separado da interface.
- **Extensibilidade total** — Tudo que falta, você cria com plugins em Python.

Você decide o quão simples ou poderoso ele será.

## ✨ Destaques

| Recurso                    | Descrição |
|---------------------------|---------|
| 🎨 **Tematização Total**   | Temas completos via arquivos JSON simples |
| 🔌 **Sistema de Plugins**  | Carregamento dinâmico e fácil de criar |
| 🌐 **Híbrido (GUI + TUI)** | Mesma lógica no Desktop (CustomTkinter) e no Terminal (Textual) |
| 🛠️ **Focado em Dev**      | Git nativo, suporte a múltiplas linguagens e syntax highlighting |
| ⚡ **Performance**         | Leve e rápido, mesmo com vários plugins |

## 📸 Screenshots
<p align="center">
  <img width="1720" height="1079" alt="image" src="https://github.com/user-attachments/assets/de38c5cb-29aa-44f6-ab69-e6452276b867" />

</p>

---

## 🛠️ Como Instalar e Usar

```bash
# Clone o repositório
git clone https://github.com/John-BrenoF/notohiis.git
cd notohiis

# Dê permissão e execute
chmod +x notohiis.sh
./notohiis.sh
```

> **Dica:** Na primeira execução, o script cria automaticamente o alias `nth`, permitindo abrir o editor de qualquer lugar com:
> ```bash
> nth
> ```

## 🧩 Turbinando com Plugins

Personalizar o Notohiis é extremamente simples. Basta colocar seus arquivos Python na pasta `plugins/` que eles são carregados automaticamente.

**Exemplos de plugins disponíveis:**

- **Auto-close** — Fecha parênteses, colchetes e aspas automaticamente
- **Color Preview** — Visualiza cores hexadecimais em tempo real
- **Git Status** — Integração completa com Git na sidebar e status bar
- **Markdown Live Preview**
- **Zen Mode** — Foco total

---

## 📂 Estrutura do Projeto

```text
notohiis/
├── core/          # Lógica principal e sistema de plugins
├── ui/            # Interface Gráfica (CustomTkinter)
├── tui/           # Interface Terminal (Textual)
├── plugins/       # ← Seus plugins vão aqui
├── midia/         # Logos e screenshots
├── themes/        # Temas em JSON
└── notohiis.sh    # Script de inicialização inteligente
```

---

<p align="center">
  <strong>Notohiis — Versão 0.3-alpha</strong><br>
  <em>"Frango com batata doce" Edition</em>
</p>

<p align="center">
  Feito com ❤️ e Python por <strong>você</strong>.
</p>

---

