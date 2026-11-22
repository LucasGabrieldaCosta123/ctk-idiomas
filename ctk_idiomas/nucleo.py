import ast
import configparser
import hashlib
import os
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk


class Idiomas:
    """
    Plug-in Plug & Play para CustomTkinter (v0.1.1):
    - Posicionamento via .place() (100% compatível com .grid() e .pack())
    - Varredura automática dos widgets de texto e seleção do CustomTkinter
    - Suporte a textos dinâmicos via `lang.t("Texto")` e callback opcional `ao_mudar_idioma`
    - Menu suspenso arredondado com engrenagem ⚙️ e janela Translate integrada
    """

    def __init__(
        self,
        janela: ctk.CTk,
        idioma_principal: str,
        arquivo="app.ini",
        ao_mudar_idioma=None,
        *,
        caminho_ini=None,
        analisar_codigo=False,
        arquivos_codigo=None,
        posicao="top-right",
        mostrar_botao=True,
    ):
        if not idioma_principal or not idioma_principal.strip():
            raise ValueError(
                "Você deve definir 'idioma_principal' (ex: 'Português (Brasil)' ou 'English')."
            )
        posicoes_validas = {
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        }
        if posicao not in posicoes_validas:
            raise ValueError(
                f"Posição inválida: {posicao!r}. Use uma destas opções: "
                f"{', '.join(sorted(posicoes_validas))}."
            )

        self.janela = janela
        self.idioma_principal = idioma_principal.strip()
        self.arquivo = os.path.abspath(
            os.path.expanduser(caminho_ini if caminho_ini is not None else arquivo)
        )
        self.ao_mudar_idioma = ao_mudar_idioma
        self.ultima_modificacao = 0
        self.menu_popup = None
        self.posicao = posicao
        self.mostrar_botao = mostrar_botao
        self.janelas = [janela]
        self._captura_inicializada = False
        self._analisar_codigo = analisar_codigo
        self._arquivos_codigo = arquivos_codigo
        self.mapa_widgets = {}
        self.mapa_valores = {}

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.optionxform = str

        if os.path.exists(self.arquivo):
            self.recarregar()
        else:
            self.config["Config"] = {"idioma": self.idioma_principal}

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

        if self.mostrar_botao:
            self._injetar_botao_engrenagem()
        else:
            self.btn_engrenagem = None
        self.janela.after(100, self._inicializar_captura)

    def _inicializar_captura(self):
        if os.path.exists(self.arquivo):
            self.recarregar()

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

        self._pre_registrar_mensagens()
        eh_ingles = (
            "english" in self.idioma_principal.lower()
            or "en" == self.idioma_principal.lower()
        )
        if "_lang_label" not in self.config[self.idioma_principal]:
            self.config[self.idioma_principal]["_lang_label"] = (
                "Language:" if eh_ingles else "Linguagem:"
            )
        if "_translate_btn" not in self.config[self.idioma_principal]:
            self.config[self.idioma_principal]["_translate_btn"] = (
                "Translate" if eh_ingles else "Traduzir"
            )

        for janela in self.janelas:
            self._capturar_janela(janela, migrar_ids_legados=janela == self.janela)

        self._captura_inicializada = True
        self.salvar()
        self.aplicar_idioma_na_tela()
        self._iniciar_monitoramento()

    def _capturar_janela(self, janela, migrar_ids_legados=False):
        titulo_atual = janela.title()
        if titulo_atual:
            chave_legada = "00_titulo" if migrar_ids_legados else None
            chave = self._chave_estavel("title", titulo_atual)
            self._registrar_texto(chave, titulo_atual, chave_legada)
            self._mapear_widget(chave, janela, "title")

        contador = 1
        for widget in self._listar_todos_widgets(janela):
            if self._pertence_ao_botao_engrenagem(
                widget
            ) or self._pertence_a_tabview_interno(widget):
                continue

            if isinstance(widget, ctk.CTkTabview):
                for (
                    nome_aba,
                    btn_aba,
                ) in widget._segmented_button._buttons_dict.items():
                    chave_legada = f"{contador:02d}" if migrar_ids_legados else None
                    chave = self._chave_estavel("tab", nome_aba)
                    self._registrar_texto(chave, nome_aba, chave_legada)
                    self._mapear_widget(chave, btn_aba, "tab")
                    contador += 1
                continue

            if isinstance(widget, ctk.CTkEntry):
                placeholder = widget.cget("placeholder_text")
                if placeholder and placeholder.strip():
                    chave_legada = f"{contador:02d}" if migrar_ids_legados else None
                    chave = self._chave_estavel("placeholder", placeholder)
                    self._registrar_texto(chave, placeholder, chave_legada)
                    self._mapear_widget(chave, widget, "placeholder")
                    contador += 1
                continue

            if isinstance(
                widget,
                (
                    ctk.CTkOptionMenu,
                    ctk.CTkComboBox,
                    ctk.CTkSegmentedButton,
                ),
            ):
                valores = tuple(widget.cget("values") or ())
                selecao = widget.get()
                chaves_valores = []
                for valor in valores:
                    valor = str(valor)
                    chave_legada = (
                        f"{contador:02d}" if migrar_ids_legados else None
                    )
                    chave = self._chave_estavel("value", valor)
                    self._registrar_texto(chave, valor, chave_legada)
                    self._mapear_widget(chave, widget, "value")
                    chaves_valores.append(chave)
                    contador += 1
                self.mapa_valores[id(widget)] = (
                    widget,
                    valores,
                    selecao,
                    chaves_valores,
                )
                continue

            texto_widget = self._obter_texto_widget(widget)
            if texto_widget and texto_widget.strip():
                chave_legada = f"{contador:02d}" if migrar_ids_legados else None
                chave = self._chave_estavel("txt", texto_widget)
                self._registrar_texto(chave, texto_widget, chave_legada)
                self._mapear_widget(chave, widget, "text")
                contador += 1

    def _mapear_widget(self, chave, widget, prop):
        destinos = self.mapa_widgets.setdefault(chave, [])
        if not any(destino is widget for destino, _ in destinos):
            destinos.append((widget, prop))

    def _chave_estavel(self, tipo, texto):
        resumo = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
        return f"{tipo}_{resumo}"

    def _registrar_texto(self, chave, texto, chave_legada=None):
        secao_base = self.config[self.idioma_principal]
        if chave in secao_base:
            return

        chave_migrada = None
        if (
            chave_legada
            and chave_legada in secao_base
            and secao_base[chave_legada] == texto
        ):
            chave_migrada = chave_legada

        secao_base[chave] = texto
        if chave_migrada:
            for secao in self.config.sections():
                if secao != self.idioma_principal and chave_migrada in self.config[secao]:
                    self.config[secao][chave] = self.config[secao][chave_migrada]
                self.config[secao].pop(chave_migrada, None)

    def t(self, texto_original: str, **kwargs) -> str:
        """Registra automaticamente mensagens dinâmicas no .ini e retorna a tradução."""
        if not texto_original:
            return ""

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

        chave_esperada = self._chave_estavel("msg", texto_original)
        mensagem_nova = chave_esperada not in self.config[self.idioma_principal]
        chave_encontrada = self._registrar_mensagem(texto_original)
        if mensagem_nova:
            self.salvar()

        idioma_ativo = self.get_config("idioma", self.idioma_principal)
        resultado = self.config.get(
            idioma_ativo, chave_encontrada, fallback=texto_original
        )
        if not resultado.strip():
            resultado = texto_original

        return resultado.format(**kwargs) if kwargs else resultado

    traduzir = t

    def _pre_registrar_mensagens(self):
        if not self._analisar_codigo:
            return

        caminhos = self._arquivos_codigo
        if caminhos is None:
            import __main__

            caminho_principal = getattr(__main__, "__file__", None)
            if not caminho_principal:
                raise ValueError(
                    "Não foi possível localizar o arquivo principal. "
                    "Informe 'arquivos_codigo' para analisar as mensagens."
                )
            caminhos = [caminho_principal]
        elif isinstance(caminhos, (str, os.PathLike)):
            caminhos = [caminhos]

        for caminho in caminhos:
            caminho = os.path.abspath(os.path.expanduser(os.fspath(caminho)))
            with open(caminho, "r", encoding="utf-8") as arquivo:
                arvore = ast.parse(arquivo.read(), filename=caminho)
            for no in ast.walk(arvore):
                if (
                    isinstance(no, ast.Call)
                    and isinstance(no.func, ast.Attribute)
                    and no.func.attr == "t"
                    and no.args
                    and isinstance(no.args[0], ast.Constant)
                    and isinstance(no.args[0].value, str)
                ):
                    self._registrar_mensagem(no.args[0].value)

        self.salvar()

    def _registrar_mensagem(self, texto):
        chave = self._chave_estavel("msg", texto)
        if chave not in self.config[self.idioma_principal]:
            chave_legada = next(
                (
                    nome
                    for nome, valor in self.config[self.idioma_principal].items()
                    if nome.startswith("msg_") and valor == texto
                ),
                None,
            )
            self._registrar_texto(chave, texto, chave_legada)
        return chave

    def registrar_janela(self, toplevel):
        """Inclui uma CTkToplevel na captura e atualização de idiomas."""
        if not isinstance(toplevel, ctk.CTkToplevel):
            raise TypeError("'toplevel' deve ser uma instância de CTkToplevel.")
        if toplevel not in self.janelas:
            self.janelas.append(toplevel)
            if self._captura_inicializada:
                toplevel.after(
                    100, lambda: self._capturar_janela(toplevel)
                )
                toplevel.after(150, self._aplicar_janela_registrada)

    def _aplicar_janela_registrada(self):
        self.aplicar_idioma_na_tela()

    def _listar_todos_widgets(self, container):
        lista = []
        for filho in container.winfo_children():
            if isinstance(filho, ctk.CTkToplevel):
                continue
            lista.append(filho)
            lista.extend(self._listar_todos_widgets(filho))
        return lista

    def _pertence_ao_botao_engrenagem(self, widget):
        return (
            self.btn_engrenagem is not None
            and (
                widget == self.btn_engrenagem
                or widget.master == self.btn_engrenagem
            )
        )

    def _pertence_a_tabview_interno(self, widget):
        if isinstance(widget.master, ctk.CTkSegmentedButton) and isinstance(
            widget.master.master, ctk.CTkTabview
        ):
            return True
        return False

    def _obter_texto_widget(self, widget):
        tipos_suportados = (
            ctk.CTkLabel,
            ctk.CTkButton,
            ctk.CTkCheckBox,
            ctk.CTkRadioButton,
            ctk.CTkSwitch,
        )
        if isinstance(widget, tipos_suportados):
            try:
                return widget.cget("text")
            except Exception:
                return None
        return None

    def aplicar_idioma_na_tela(self):
        idioma_ativo = self.get_config("idioma", self.idioma_principal)

        for chave, destinos in self.mapa_widgets.items():
            texto_original = self.config.get(
                self.idioma_principal, chave, fallback=""
            )
            texto_final = self.config.get(
                idioma_ativo, chave, fallback=texto_original
            )
            if not texto_final.strip():
                texto_final = texto_original
            for widget, prop in destinos:
                if not widget.winfo_exists():
                    continue
                if prop == "title":
                    widget.title(texto_final)
                elif prop == "text":
                    widget.configure(text=texto_final)
                elif prop == "placeholder":
                    widget.configure(placeholder_text=texto_final)
                elif prop == "tab":
                    widget.configure(text=texto_final)

        for (
            widget,
            valores_originais,
            selecao_original,
            chaves,
        ) in self.mapa_valores.values():
            if not widget.winfo_exists():
                continue
            valores_traduzidos = [
                self._texto_traduzido(chave) for chave in chaves
            ]
            selecao_atual = widget.get()
            indice_selecao = None
            for indice, valor_original in enumerate(valores_originais):
                valor_traduzido = valores_traduzidos[indice]
                if selecao_atual in (valor_original, valor_traduzido):
                    indice_selecao = indice
                    break
            if indice_selecao is None and selecao_atual == selecao_original:
                indice_selecao = next(
                    (
                        indice
                        for indice, valor in enumerate(valores_originais)
                        if valor == selecao_original
                    ),
                    None,
                )
            widget.configure(values=valores_traduzidos)
            if indice_selecao is not None:
                widget.set(valores_traduzidos[indice_selecao])

        if self.ao_mudar_idioma:
            self.ao_mudar_idioma()

        if self.btn_engrenagem is not None:
            self.btn_engrenagem.lift()

    def _texto_traduzido(self, chave):
        idioma_ativo = self.get_config("idioma", self.idioma_principal)
        original = self.config.get(self.idioma_principal, chave, fallback="")
        traduzido = self.config.get(idioma_ativo, chave, fallback=original)
        return traduzido if traduzido.strip() else original

    def _injetar_botao_engrenagem(self):
        """Usa .place() para não conflitar com .grid() ou .pack()."""
        self.btn_engrenagem = ctk.CTkButton(
            self.janela,
            text="⚙️",
            width=34,
            height=34,
            corner_radius=0,
            font=("Segoe UI Emoji", 15),
            fg_color="transparent",
            hover_color="transparent",
            border_width=0,
            command=self._alternar_menu,
        )
        relx = 0.0 if self.posicao.endswith("left") else 1.0
        rely = 0.0 if self.posicao.startswith("top") else 1.0
        x = 10 if relx == 0.0 else -10
        y = 8 if rely == 0.0 else -8
        anchor = ("n" if rely == 0.0 else "s") + (
            "w" if relx == 0.0 else "e"
        )
        self.btn_engrenagem.place(
            relx=relx, rely=rely, x=x, y=y, anchor=anchor
        )
        self.btn_engrenagem.lift()

    def abrir_menu(self):
        """Abre o menu de idiomas, inclusive quando o botão automático está desativado."""
        self._alternar_menu()

    def _alternar_menu(self):
        if self.menu_popup is not None and self.menu_popup.winfo_exists():
            self._fechar_menu()
            return
        self._abrir_menu()

    def _fechar_menu(self, event=None):
        if self.menu_popup is not None and self.menu_popup.winfo_exists():
            self.menu_popup.destroy()
        self.menu_popup = None

    def _abrir_menu(self):
        popup = ctk.CTkToplevel(self.janela)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        self.menu_popup = popup

        cor_chave = "#000001"
        popup.configure(fg_color=cor_chave)
        try:
            popup.wm_attributes("-transparentcolor", cor_chave)
        except tk.TclError:
            pass

        card = ctk.CTkFrame(
            popup,
            corner_radius=12,
            border_width=1,
            border_color=("#CCCCCC", "#3E3E42"),
            fg_color=("#F9F9F9", "#252526"),
        )
        card.pack(fill="both", expand=True, padx=2, pady=2)

        lbl_titulo = ctk.CTkLabel(
            card,
            text=self.texto("_lang_label"),
            font=("Segoe UI", 11, "bold"),
            text_color=("#6E6E73", "#9A9A9E"),
            anchor="w",
        )
        lbl_titulo.pack(fill="x", padx=14, pady=(10, 4))

        idioma_atual = self.get_config("idioma", self.idioma_principal)
        idiomas = [s for s in self.config.sections() if s != "Config"]

        for lang in idiomas:
            ativo = lang == idioma_atual
            prefixo = "✓  " if ativo else "     "
            btn_lang = ctk.CTkButton(
                card,
                text=f"{prefixo}{lang}",
                anchor="w",
                height=30,
                corner_radius=7,
                font=("Segoe UI", 12, "bold" if ativo else "normal"),
                fg_color=("#E5F1FB", "#1F6AA5") if ativo else "transparent",
                text_color=("#005A9E", "#FFFFFF")
                if ativo
                else ("#1D1D1F", "#E5E5E7"),
                hover_color=("#D6E8F8", "#2B79B8")
                if ativo
                else ("#EAEAEA", "#333337"),
                command=lambda l=lang: self._selecionar_idioma(l),
            )
            btn_lang.pack(fill="x", padx=6, pady=1)

        separador = ctk.CTkFrame(
            card, height=1, fg_color=("#DCDCDC", "#3A3A3D")
        )
        separador.pack(fill="x", padx=10, pady=6)

        btn_traduzir = ctk.CTkButton(
            card,
            text=f"🌐  {self.texto('_translate_btn')}",
            anchor="w",
            height=32,
            corner_radius=7,
            font=("Segoe UI", 12),
            fg_color="transparent",
            text_color=("#1D1D1F", "#E5E5E7"),
            hover_color=("#EAEAEA", "#333337"),
            command=self._abrir_tradutor_do_menu,
        )
        btn_traduzir.pack(fill="x", padx=6, pady=(0, 8))

        popup.update_idletasks()
        largura_menu = max(195, popup.winfo_reqwidth())
        altura_menu = popup.winfo_reqheight()

        if self.btn_engrenagem is not None:
            btn_x = self.btn_engrenagem.winfo_rootx()
            btn_y = self.btn_engrenagem.winfo_rooty()
            btn_w = self.btn_engrenagem.winfo_width()
            btn_h = self.btn_engrenagem.winfo_height()
        else:
            btn_x = self.janela.winfo_rootx()
            btn_y = self.janela.winfo_rooty()
            if self.posicao.startswith("bottom"):
                btn_y += self.janela.winfo_height()
            btn_w = self.janela.winfo_width()
            btn_h = 0

        pos_x = btn_x if self.posicao.endswith("left") else btn_x + btn_w - largura_menu
        if self.posicao.startswith("top"):
            pos_y = btn_y + btn_h + 4
        else:
            pos_y = btn_y - altura_menu - 4

        popup.geometry(f"{largura_menu}x{altura_menu}+{pos_x}+{pos_y}")
        popup.focus_force()
        popup.bind("<FocusOut>", self._verificar_perda_foco)
        popup.bind("<Escape>", self._fechar_menu)

    def _verificar_perda_foco(self, event=None):
        if self.menu_popup is None or not self.menu_popup.winfo_exists():
            return
        foco_atual = self.janela.focus_get()
        if foco_atual is None or not str(foco_atual).startswith(
            str(self.menu_popup)
        ):
            self._fechar_menu()

    def _selecionar_idioma(self, novo_idioma):
        self._fechar_menu()
        self.set_config("idioma", novo_idioma)
        self.aplicar_idioma_na_tela()

    def _abrir_tradutor_do_menu(self):
        self._fechar_menu()
        JanelaTradutor(self.janela, self)

    def _iniciar_monitoramento(self):
        if self.arquivo_foi_modificado():
            try:
                self.recarregar()
                self.aplicar_idioma_na_tela()
            except configparser.Error:
                pass
        self.janela.after(1000, self._iniciar_monitoramento)

    def recarregar(self):
        self.config.clear()
        self.config.read(self.arquivo, encoding="utf-8")
        self.ultima_modificacao = os.path.getmtime(self.arquivo)

    def arquivo_foi_modificado(self):
        if not os.path.exists(self.arquivo):
            return False
        return os.path.getmtime(self.arquivo) != self.ultima_modificacao

    def texto(self, chave):
        idioma = self.config.get(
            "Config", "idioma", fallback=self.idioma_principal
        )
        original = self.config.get(
            self.idioma_principal, chave, fallback=f"[{chave}]"
        )
        res = self.config.get(idioma, chave, fallback=original)
        return res if res.strip() else original

    def get_config(self, chave, padrao=""):
        return self.config.get("Config", chave, fallback=padrao)

    def set_config(self, chave, valor):
        self.config["Config"][chave] = str(valor)
        self.salvar()

    def salvar(self):
        os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
        with open(self.arquivo, "w", encoding="utf-8") as f:
            self.config.write(f)
        self.ultima_modificacao = os.path.getmtime(self.arquivo)


class JanelaTradutor(ctk.CTkToplevel):
    """Janela integrada de tradução com pré-preenchimento do idioma base."""

    def __init__(self, master, gerenciador: Idiomas):
        super().__init__(master)
        self.ini = gerenciador
        self.dados_traducao = {}
        self.chave_atual = None

        self.title("Translate")
        self.geometry("820x520")
        self.grab_set()

        self._criar_topo()
        self._criar_tabela()
        self._criar_rodape()
        self._atualizar_tabela()

    def _criar_topo(self):
        frame_topo = ctk.CTkFrame(self)
        frame_topo.pack(fill="x", padx=12, pady=(12, 6))

        idiomas = [s for s in self.ini.config.sections() if s != "Config"]
        idioma_padrao = idiomas[0] if idiomas else self.ini.idioma_principal

        frame_base = ctk.CTkFrame(frame_topo, fg_color="transparent")
        frame_base.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(frame_base, text="Select Your Language (Base):").pack(
            anchor="w"
        )
        self.combo_base = ctk.CTkOptionMenu(
            frame_base,
            values=idiomas,
            command=lambda e: self._atualizar_tabela(base=e),
            width=180,
        )
        atual = self.ini.get_config("idioma", idioma_padrao)
        self.combo_base.set(atual if atual in idiomas else idioma_padrao)
        self.combo_base.pack()

        frame_novo = ctk.CTkFrame(frame_topo, fg_color="transparent")
        frame_novo.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(frame_novo, text="Write or Select Target Language:").pack(
            anchor="w"
        )
        self.entry_novo_idioma = ctk.CTkComboBox(
            frame_novo,
            values=idiomas,
            command=lambda e: self._atualizar_tabela(alvo=e),
            width=190,
        )
        self.entry_novo_idioma.set("")
        self.entry_novo_idioma.bind(
            "<Return>", lambda _: self._atualizar_tabela()
        )
        self.entry_novo_idioma.bind(
            "<FocusOut>", lambda _: self._atualizar_tabela()
        )
        self.entry_novo_idioma.pack()

        frame_btns = ctk.CTkFrame(frame_topo, fg_color="transparent")
        frame_btns.pack(side="right", padx=10, pady=8)

        ctk.CTkButton(
            frame_btns,
            text="Save Language",
            width=130,
            command=self._salvar_idioma,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_btns,
            text="Copy to Clipboard",
            width=140,
            fg_color="#3B8ED0",
            command=self._copiar_ini,
        ).pack(side="left", padx=5)

    def _criar_tabela(self):
        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(fill="both", expand=True, padx=12, pady=6)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        colunas = ("id", "original", "traducao")
        self.tree = ttk.Treeview(
            frame_tabela, columns=colunas, show="headings", selectmode="browse"
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("original", text="Base Language String")
        self.tree.heading("traducao", text="Your Language String")

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("original", width=350, anchor="w")
        self.tree.column("traducao", width=350, anchor="w")

        scroll = ttk.Scrollbar(
            frame_tabela, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar_linha)

    def _criar_rodape(self):
        frame_rodape = ctk.CTkFrame(self)
        frame_rodape.pack(fill="x", padx=12, pady=(6, 12))

        ctk.CTkLabel(
            frame_rodape,
            text="To go to another line, use Up/Down arrows or click on the table above:",
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=10, pady=(6, 2))

        frame_caixas = ctk.CTkFrame(frame_rodape, fg_color="transparent")
        frame_caixas.pack(fill="x", padx=10, pady=(0, 10))

        self.txt_original = ctk.CTkTextbox(frame_caixas, height=85, width=380)
        self.txt_original.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.txt_original.configure(state="disabled")

        self.txt_traducao = ctk.CTkTextbox(frame_caixas, height=85, width=380)
        self.txt_traducao.pack(
            side="right", fill="both", expand=True, padx=(6, 0)
        )
        self.txt_traducao.bind("<KeyRelease>", self._ao_digitar_traducao)
        self.txt_traducao.bind("<Up>", lambda e: self._mover_selecao(-1))
        self.txt_traducao.bind("<Down>", lambda e: self._mover_selecao(1))

    def _atualizar_tabela(self, base=None, alvo=None):
        self.ini.recarregar()
        self.tree.delete(*self.tree.get_children())
        self.dados_traducao.clear()

        idioma_base = base if base else self.combo_base.get()
        idioma_alvo = alvo if alvo else self.entry_novo_idioma.get().strip()

        if idioma_base not in self.ini.config:
            return

        for chave, valor_base in self.ini.config[idioma_base].items():
            valor_trad = valor_base
            if (
                idioma_alvo in self.ini.config
                and chave in self.ini.config[idioma_alvo]
            ):
                existente = self.ini.config[idioma_alvo][chave]
                if existente and existente.strip():
                    valor_trad = existente

            self.dados_traducao[chave] = valor_trad
            self.tree.insert(
                "", "end", iid=chave, values=(chave, valor_base, valor_trad)
            )

        filhos = self.tree.get_children()
        if filhos:
            self.tree.selection_set(filhos[0])
            self._ao_selecionar_linha()

    def _ao_selecionar_linha(self, event=None):
        selecionado = self.tree.selection()
        if not selecionado:
            return

        self.chave_atual = selecionado[0]
        valores = self.tree.item(self.chave_atual, "values")

        self.txt_original.configure(state="normal")
        self.txt_original.delete("1.0", "end")
        self.txt_original.insert("1.0", valores[1])
        self.txt_original.configure(state="disabled")

        self.txt_traducao.delete("1.0", "end")
        self.txt_traducao.insert(
            "1.0", self.dados_traducao.get(self.chave_atual, "")
        )

    def _ao_digitar_traducao(self, event=None):
        if not self.chave_atual:
            return
        texto = self.txt_traducao.get("1.0", "end-1c").replace("\n", "\\n")
        self.dados_traducao[self.chave_atual] = texto

        valor_original = self.tree.item(self.chave_atual, "values")[1]
        self.tree.item(
            self.chave_atual, values=(self.chave_atual, valor_original, texto)
        )

    def _mover_selecao(self, direcao):
        filhos = self.tree.get_children()
        if not filhos or not self.chave_atual:
            return "break"
        idx = filhos.index(self.chave_atual) + direcao
        if 0 <= idx < len(filhos):
            self.tree.selection_set(filhos[idx])
            self.tree.see(filhos[idx])
            self._ao_selecionar_linha()
        return "break"

    def _gerar_bloco_ini(self, nome_idioma):
        linhas = [f"[{nome_idioma}]"]
        for chave, trad in self.dados_traducao.items():
            valor_original = self.tree.item(chave, "values")[1]
            texto_final = trad if trad.strip() else valor_original
            linhas.append(f"{chave} = {texto_final}")
        return "\n".join(linhas)

    def _salvar_idioma(self):
        novo_idioma = self.entry_novo_idioma.get().strip()
        if not novo_idioma or novo_idioma == "Config":
            messagebox.showwarning(
                "Aviso", "Digite um nome válido para o idioma.", parent=self
            )
            return

        if novo_idioma not in self.ini.config:
            self.ini.config.add_section(novo_idioma)

        for chave, trad in self.dados_traducao.items():
            valor_original = self.tree.item(chave, "values")[1]
            texto_final = trad if trad.strip() else valor_original
            self.ini.config[novo_idioma][chave] = texto_final

        self.ini.set_config("idioma", novo_idioma)
        idiomas_atualizados = [
            s for s in self.ini.config.sections() if s != "Config"
        ]
        self.combo_base.configure(values=idiomas_atualizados)
        self.entry_novo_idioma.configure(values=idiomas_atualizados)
        self.ini.aplicar_idioma_na_tela()
        messagebox.showinfo(
            "Sucesso", f"Idioma '{novo_idioma}' salvo e aplicado!", parent=self
        )

    def _copiar_ini(self):
        nome = self.entry_novo_idioma.get().strip() or "Novo_Idioma"
        bloco = self._gerar_bloco_ini(nome)
        self.clipboard_clear()
        self.clipboard_append(bloco)
        messagebox.showinfo(
            "Copiado",
            "Tradução copiada para a área de transferência!",
            parent=self,
        )