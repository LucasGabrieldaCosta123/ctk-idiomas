import configparser
import os
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk


class Idiomas:
    """
    Plug-in Plug & Play para CustomTkinter:
    - Captura automática de título, labels, botões, checkboxes, switches, CTkEntry e CTkTabview
    - Função auxiliar `lang.t("Texto dinâmico")` para mensagens em tempo de execução
    - Menu suspenso arredondado com engrenagem ⚙️
    - Janela Translate pré-preenchida para traduzir apenas o que você souber
    """

    def __init__(self, janela: ctk.CTk, idioma_principal: str, arquivo="app.ini"):
        if not idioma_principal or not idioma_principal.strip():
            raise ValueError(
                "Você deve definir 'idioma_principal' (ex: 'Português (Brasil)' ou 'English')."
            )

        self.janela = janela
        self.idioma_principal = idioma_principal.strip()
        self.arquivo = os.path.abspath(arquivo)
        self.ultima_modificacao = 0
        self.menu_popup = None

        # {chave: (widget, propriedade)}
        self.mapa_widgets = {}

        self.config = configparser.ConfigParser(interpolation=None)
        self.config.optionxform = str

        if os.path.exists(self.arquivo):
            self.recarregar()
        else:
            self.config["Config"] = {"idioma": self.idioma_principal}

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

        self._injetar_barra_superior()
        self.janela.after(100, self._inicializar_captura)

    def _inicializar_captura(self):
        if os.path.exists(self.arquivo):
            self.recarregar()

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

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

        # 1. Título da janela
        titulo_atual = self.janela.title()
        if titulo_atual:
            self.mapa_widgets["00_titulo"] = (self.janela, "title")
            if "00_titulo" not in self.config[self.idioma_principal]:
                self.config[self.idioma_principal]["00_titulo"] = titulo_atual

        # 2. Varre todos os widgets da janela (incluindo CTkTabview e CTkEntry)
        contador = 1
        for widget in self._listar_todos_widgets(self.janela):
            if self._pertence_a_barra_topo(
                widget
            ) or self._pertence_a_tabview_interno(widget):
                continue

            if isinstance(widget, ctk.CTkTabview):
                for (
                    nome_aba,
                    btn_aba,
                ) in widget._segmented_button._buttons_dict.items():
                    chave = f"{contador:02d}"
                    self.mapa_widgets[chave] = (btn_aba, "tab")
                    if chave not in self.config[self.idioma_principal]:
                        self.config[self.idioma_principal][chave] = nome_aba
                    contador += 1
                continue

            if isinstance(widget, ctk.CTkEntry):
                placeholder = widget.cget("placeholder_text")
                if placeholder and placeholder.strip():
                    chave = f"{contador:02d}"
                    self.mapa_widgets[chave] = (widget, "placeholder")
                    if chave not in self.config[self.idioma_principal]:
                        self.config[self.idioma_principal][chave] = placeholder
                    contador += 1
                continue

            texto_widget = self._obter_texto_widget(widget)
            if texto_widget and texto_widget.strip():
                chave = f"{contador:02d}"
                self.mapa_widgets[chave] = (widget, "text")
                if chave not in self.config[self.idioma_principal]:
                    self.config[self.idioma_principal][chave] = texto_widget
                contador += 1

        self.salvar()
        self.aplicar_idioma_na_tela()
        self._iniciar_monitoramento()

    # --- FUNÇÃO PARA TEXTOS DINÂMICOS (messagebox, alertas, textos pós-clique) ---
    def t(self, texto_original: str, **kwargs) -> str:
        """
        Registra automaticamente mensagens dinâmicas no .ini e retorna a tradução.
        Exemplo: messagebox.showinfo("Aviso", lang.t("Arquivo salvo com sucesso!"))
        """
        if not texto_original:
            return ""

        if self.idioma_principal not in self.config:
            self.config.add_section(self.idioma_principal)

        # Procura se esse texto dinâmico já foi registrado antes
        chave_encontrada = None
        for k, v in self.config[self.idioma_principal].items():
            if k.startswith("msg_") and v == texto_original:
                chave_encontrada = k
                break

        # Se ainda não existe no .ini, cria uma chave msg_01, msg_02...
        if not chave_encontrada:
            msgs_existentes = [
                k
                for k in self.config[self.idioma_principal].keys()
                if k.startswith("msg_")
            ]
            chave_encontrada = f"msg_{len(msgs_existentes) + 1:02d}"
            self.config[self.idioma_principal][chave_encontrada] = (
                texto_original
            )
            self.salvar()

        idioma_ativo = self.get_config("idioma", self.idioma_principal)
        resultado = self.config.get(
            idioma_ativo, chave_encontrada, fallback=texto_original
        )
        if not resultado.strip():
            resultado = texto_original

        return resultado.format(**kwargs) if kwargs else resultado

    # Alias caso prefira escrever lang.traduzir("...")
    traduzir = t

    def _listar_todos_widgets(self, container):
        lista = []
        for filho in container.winfo_children():
            if isinstance(filho, ctk.CTkToplevel):
                continue
            lista.append(filho)
            lista.extend(self._listar_todos_widgets(filho))
        return lista

    def _pertence_a_barra_topo(self, widget):
        atual = widget
        while atual is not None:
            if atual == self.barra_topo:
                return True
            atual = atual.master
        return False

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

        for chave, (widget, prop) in self.mapa_widgets.items():
            if not widget.winfo_exists():
                continue

            texto_original = self.config.get(
                self.idioma_principal, chave, fallback=""
            )
            texto_final = self.config.get(
                idioma_ativo, chave, fallback=texto_original
            )
            if not texto_final.strip():
                texto_final = texto_original

            if prop == "title":
                self.janela.title(texto_final)
            elif prop == "text":
                widget.configure(text=texto_final)
            elif prop == "placeholder":
                widget.configure(placeholder_text=texto_final)
            elif prop == "tab":
                widget.configure(text=texto_final)

    def _injetar_barra_superior(self):
        self.barra_topo = ctk.CTkFrame(
            self.janela, fg_color="transparent", height=36
        )
        self.barra_topo.pack(side="top", fill="x", padx=8, pady=(6, 0))

        self.btn_engrenagem = ctk.CTkButton(
            self.barra_topo,
            text="⚙️",
            width=34,
            height=34,
            corner_radius=8,
            font=("Segoe UI Emoji", 15),
            fg_color="transparent",
            hover_color=("#E2E2E2", "#2F2F2F"),
            command=self._alternar_menu,
        )
        self.btn_engrenagem.pack(side="right")

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

        btn_x = self.btn_engrenagem.winfo_rootx()
        btn_y = self.btn_engrenagem.winfo_rooty()
        btn_w = self.btn_engrenagem.winfo_width()
        btn_h = self.btn_engrenagem.winfo_height()

        pos_x = (btn_x + btn_w) - largura_menu
        pos_y = btn_y + btn_h + 4

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
        with open(self.arquivo, "w", encoding="utf-8") as f:
            self.config.write(f)
        self.ultima_modificacao = os.path.getmtime(self.arquivo)


class JanelaTradutor(ctk.CTkToplevel):
    """
    Janela integrada de tradução:
    Já preenche todos os campos com os textos do idioma selecionado,
    permitindo traduzir apenas o que você souber e manter o resto original.
    """

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
        """
        Preenche a coluna da direita com as traduções já existentes do idioma alvo;
        se o idioma alvo ainda não existir ou faltar alguma linha, já preenche com
        o texto do idioma base para você editar apenas o que souber!
        """
        self.ini.recarregar()
        self.tree.delete(*self.tree.get_children())
        self.dados_traducao.clear()

        idioma_base = base if base else self.combo_base.get()
        idioma_alvo = alvo if alvo else self.entry_novo_idioma.get().strip()

        if idioma_base not in self.ini.config:
            return

        for chave, valor_base in self.ini.config[idioma_base].items():
            # Começa preenchido com o texto base
            valor_trad = valor_base
            # Se o idioma alvo já existe e tem texto não-vazio nessa chave, usa ele
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