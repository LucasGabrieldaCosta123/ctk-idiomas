# 🌐 ctk-idiomas

Sistema **Plug & Play** de internacionalização (i18n), troca de idiomas em tempo real e editor visual de traduções para aplicativos feitos com **CustomTkinter**.

Com apenas **uma linha de código**, o `ctk-idiomas` injeta um menu suspenso moderno no topo da sua janela, captura automaticamente os textos da interface, gera o arquivo `.ini` e permite que você ou qualquer usuário crie novas traduções sem mexer no código-fonte.

---

## ✨ Funcionalidades

- **Zero Configuração de Layout:** Injeta automaticamente um botão de engrenagem (`⚙️`) no canto superior direito da janela com menu suspenso arredondado.
- **Varredura Automática de Widgets:** Detecta e traduz sozinho:
  - Título da janela (`app.title`)
  - Textos de `CTkLabel`, `CTkButton`, `CTkCheckBox`, `CTkRadioButton` e `CTkSwitch`
  - Campos de entrada `CTkEntry` (`placeholder_text`)
  - Títulos das abas de `CTkTabview`
- **Mensagens Dinâmicas (`lang.t`):** Registra e traduz textos exibidos apenas em tempo de execução (como `messagebox` ou textos pós-clique), com suporte a variáveis (`{nome}`).
- **Editor Visual Integrado (`Translate`):** Janela embutida com tabela lado a lado, navegação por teclado (`↑` / `↓`), pré-preenchimento inteligente (mantém o texto original nas frases não traduzidas) e exportação para a área de transferência.
- **Hot Reload em Tempo Real:** Monitora o arquivo `app.ini` em segundo plano — editou e salvou no bloco de notas, a interface atualiza na hora sem reiniciar o app.

---

## 🛠️ Ferramentas e Tecnologias Utilizadas

- **[Python 3.8+](https://python.org):** Linguagem base do projeto.
- **[CustomTkinter](https://github.com):** Construção dos componentes visuais modernos, janelas auxiliares e menu suspenso estilizado.
- **`configparser` (Biblioteca Padrão):** Leitura, escrita e gerenciamento estruturado dos arquivos `.ini` em UTF-8.
- **`tkinter` / `ttk` (Biblioteca Padrão):** Renderização da tabela de tradução (`Treeview`) e controle de eventos de foco/teclado.
- **`setuptools`:** Empacotamento padrão PEP 621 via `pyproject.toml` para instalação universal via `pip`.

---

## 📦 Instalação

### Instalação via GitHub/Python
Em qualquer projeto ou computador, instale diretamente pelo terminal:

```bash
pip install ctk-idiomas
```

---

## 🚀 Como Usar

Basta importar `Idiomas` e iniciá-lo logo após criar a janela principal, informando o **`idioma_principal`** em que o aplicativo foi escrito:

```python
from tkinter import messagebox
import customtkinter as ctk
from ctk_idiomas import Idiomas

app = ctk.CTk()
app.title("Meu Aplicativo")
app.geometry("460x320")

# 1. Inicializa o sistema de idiomas (injeta o botão ⚙️ automaticamente)
lang = Idiomas(app, idioma_principal="Português (Brasil)")

# 2. Crie sua interface normalmente
abas = ctk.CTkTabview(app)
abas.pack(fill="both", expand=True, padx=15, pady=10)

aba_inicio = abas.add("Início")
aba_sobre = abas.add("Sobre")

entrada = ctk.CTkEntry(aba_inicio, placeholder_text="Digite seu nome")
entrada.pack(pady=(20, 10), fill="x", padx=20)

def ao_clicar():
    nome = entrada.get() or "Visitante"
    # 3. Use lang.t() para mensagens dinâmicas em tempo de execução
    messagebox.showinfo(
        lang.t("Aviso"),
        lang.t("Olá, {nome}! Bem-vindo ao sistema.", nome=nome)
    )

ctk.CTkButton(aba_inicio, text="Confirmar", command=ao_clicar).pack(pady=10)
ctk.CTkLabel(aba_sobre, text="Versão 1.0").pack(pady=30)

app.mainloop()
```

---

## ⚙️ Como Funciona por Dentro

1. **Captura Pós-Montagem (`after`):** Assim que o aplicativo inicia, o `Idiomas` aguarda a montagem dos widgets na tela e percorre recursivamente toda a árvore de componentes (`winfo_children`), mapeando cada widget para um ID numérico (`01`, `02`, `03`...).
2. **Geração do `app.ini`:** Na primeira execução, cria o arquivo `app.ini` em UTF-8 na pasta do projeto contendo a seção `[Config]` e a seção do idioma principal definida pelo desenvolvedor.
3. **Fallback Seguro:** Caso um usuário crie uma tradução parcial (traduzindo apenas algumas frases), o sistema preenche automaticamente as linhas restantes com o texto do idioma base, evitando campos vazios ou erros na interface.
4. **Monitoramento de Arquivo:** A cada `1000ms`, verifica o *timestamp* (`os.path.getmtime`) do `app.ini`. Se houver alteração externa no disco, relê o arquivo e reaplica os textos na janela instantaneamente.

---

## 📄 Exemplo do `app.ini` Gerado

```ini
[Config]
idioma = Português (Brasil)

[Português (Brasil)]
_lang_label = Linguagem:
_translate_btn = Traduzir
00_titulo = Meu Aplicativo
01 = Início
02 = Sobre
03 = Digite seu nome
04 = Confirmar
05 = Versão 1.0
msg_01 = Aviso
msg_02 = Olá, {nome}! Bem-vindo ao sistema.
```

---

## 📁 Estrutura do Pacote

```text
ctk_idiomas/
├── pyproject.toml       # Metadados e dependências do pacote
├── README.md            # Documentação do projeto
└── ctk_idiomas/
    ├── __init__.py      # Exportação pública da classe Idiomas
    └── nucleo.py        # Gerenciador INI, menu suspenso e janela Translate
```

---

## 📝 Licença

Este projeto é de uso livre para projetos pessoais e comerciais.
