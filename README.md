# 🌐 ctk-idiomas

Sistema **Plug & Play** de internacionalização (i18n), troca de idiomas em tempo real e editor visual de traduções para aplicativos feitos com **CustomTkinter**.

Com apenas **uma linha de código**, o `ctk-idiomas` injeta um menu suspenso moderno no topo da sua janela, captura automaticamente os textos da interface, gera o arquivo `.ini` e permite que você ou qualquer usuário crie novas traduções sem mexer no código-fonte.

---

## ✨ Funcionalidades

- **Configuração do menu:** O botão de engrenagem (`⚙️`) pode ser posicionado nos quatro cantos, ocultado ou aberto por um botão próprio. Seu fundo é transparente.
- **Varredura Automática de Widgets:** Detecta e traduz sozinho:
  - Título da janela (`app.title`)
  - Textos de `CTkLabel`, `CTkButton`, `CTkCheckBox`, `CTkRadioButton` e `CTkSwitch`
  - Campos de entrada `CTkEntry` (`placeholder_text`)
  - Títulos das abas de `CTkTabview`
  - Opções e seleção atual de `CTkOptionMenu`, `CTkComboBox` e `CTkSegmentedButton`
- **Mensagens Dinâmicas (`lang.t`):** Registra e traduz textos exibidos em tempo de execução (como `messagebox` ou textos pós-clique), com suporte a variáveis (`{nome}`). Opcionalmente, analisa chamadas literais no código com `ast` durante a inicialização.
- **Janelas Secundárias:** Registra `CTkToplevel` criadas depois da janela principal para captura e atualização de idioma.
- **Arquivo configurável:** `caminho_ini` permite salvar o INI em um local escolhido, inclusive em uma pasta do usuário.
- **Editor Visual Integrado (`Translate`):** Janela embutida com tabela lado a lado, navegação por teclado (`↑` / `↓`), edição manual no campo inferior direito, pré-preenchimento inteligente (mantém o texto original nas frases não traduzidas) e exportação para a área de transferência. O pacote não traduz automaticamente o conteúdo.
- **Hot Reload em Tempo Real:** Monitora o arquivo `app.ini` em segundo plano — editou e salvou no bloco de notas, a interface atualiza na hora sem reiniciar o app.

---

## 🛠️ Ferramentas e Tecnologias Utilizadas

- **[Python 3.8+](https://www.python.org/downloads/release/python-3100/):** Linguagem base do projeto.
- **[CustomTkinter](https://github.com/tomschimansky/customtkinter):** Construção dos componentes visuais modernos, janelas auxiliares e menu suspenso estilizado.
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

### Opções

Os parâmetros abaixo são opcionais; os padrões preservam o comportamento atual:

```python
lang = Idiomas(
    app,
    idioma_principal="Português (Brasil)",
    caminho_ini="~/AppData/Local/MeuApp/app.ini",
    analisar_codigo=True,  # analisa o arquivo principal da aplicação
    posicao="bottom-right",  # top-left, top-right, bottom-left ou bottom-right
)
```

Para analisar outros arquivos Python, passe seus caminhos em `arquivos_codigo` junto com `analisar_codigo=True`. São pré-registradas chamadas com uma string literal como primeiro argumento, por exemplo `lang.t("Falha de conexão")`.

Para continuar editando um idioma existente, use o idioma principal como base e selecione ou digite o idioma de destino existente. As traduções já preenchidas são carregadas; as que ainda estiverem em branco usam o texto original como fallback.

Para ocultar a engrenagem e abrir o menu a partir de um controle próprio:

```python
lang = Idiomas(
    app, idioma_principal="Português (Brasil)", mostrar_botao=False
)
ctk.CTkButton(app, text="Idiomas", command=lang.abrir_menu).pack()
```

Registre cada janela secundária depois de criar seus widgets:

```python
janela = ctk.CTkToplevel(app)
ctk.CTkLabel(janela, text="Configurações").pack()
lang.registrar_janela(janela)
```

---

## ⚙️ Como Funciona por Dentro

1. **Captura Pós-Montagem (`after`):** Assim que o aplicativo inicia, o `Idiomas` aguarda a montagem dos widgets e percorre recursivamente a árvore de componentes (`winfo_children`). Os textos recebem chaves estáveis derivadas de seu conteúdo, evitando que a inserção ou reordenação de widgets desloque as traduções. Chaves numéricas de versões anteriores são migradas quando o texto original coincide.
2. **Geração do INI:** Na primeira execução, cria o arquivo em UTF-8 com a seção `[Config]` e a seção do idioma principal. O caminho padrão continua sendo `app.ini` na pasta atual; `caminho_ini` permite substituí-lo.
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
title_a1b2c3d4e5f6 = Meu Aplicativo
tab_112233445566 = Início
tab_aabbccddeeff = Sobre
placeholder_123456789abc = Digite seu nome
txt_abcdef123456 = Confirmar
txt_123abc456def = Versão 1.0
msg_a12b34c56d78 = Aviso
msg_9876abcdef01 = Olá, {nome}! Bem-vindo ao sistema.
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
