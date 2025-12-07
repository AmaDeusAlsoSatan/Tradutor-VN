import customtkinter as ctk
import json
import os
import threading
import time
import re
import queue  # <--- NOVO: Para gerenciar a fila de pedidos
from dotenv import load_dotenv
import google.generativeai as genai
from tkinter import messagebox
import tkinter as tk

# --- CONFIGURAÇÕES ---
PASTA_BASE_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc" 
ARQUIVO_VISUAL = os.path.join(PASTA_BASE_JOGO, "game", "estado_visual.json")

# Arquivos de Tradução
ARQUIVO_SCRIPT = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "script.rpy")
# O RenPy pode criar na raiz da TL ou dentro de screens/ TL. Ajuste após gerar a tradução:
ARQUIVO_CHOICES = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "screens", "wordchoice.rpy") 
if not os.path.exists(ARQUIVO_CHOICES):
    # Fallback caso ele crie na raiz
    ARQUIVO_CHOICES = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "wordchoice.rpy")

ARQUIVO_IDENTIDADE = "identidade.json"
ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configura IA
if API_KEY:
    genai.configure(api_key=API_KEY)
    # Tenta usar o Flash, se não der, usa o Pro
    try: MODELO_IA = genai.GenerativeModel('models/gemini-2.0-flash')
    except: MODELO_IA = genai.GenerativeModel('models/gemini-pro')

# --- FUNÇÕES DE MEMÓRIA (DATASET) ---
def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try: return json.load(open(arquivo, "r", encoding="utf-8"))
        except: return [] if "dataset" in arquivo else {}
    return [] if "dataset" in arquivo else {}

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def aprender_traducao_logica(original, correcao):
    """Lógica de Promoção: Remove do Silver e Salva no Gold"""
    if not original or not correcao: return
    
    # 1. Carrega bases
    gold = carregar_json(ARQUIVO_OURO)
    silver = carregar_json(ARQUIVO_PRATA)
    
    # 2. Remove do Silver (se existir lá)
    len_antes = len(silver)
    silver = [item for item in silver if item['en'] != original]
    if len(silver) < len_antes:
        salvar_json(ARQUIVO_PRATA, silver)
        print(f"[Dataset] Removido do Silver: {original[:20]}...")

    # 3. Adiciona ou Atualiza no Gold
    encontrado = False
    for item in gold:
        if item['en'] == original:
            item['pt'] = correcao
            item['score'] = 100.0
            item['contexto_vn'] = "Overlay_V3_Humano"
            encontrado = True
            break
    
    if not encontrado:
        gold.append({"en": original, "pt": correcao, "score": 100.0, "contexto_vn": "Overlay_V3_Humano"})
    
    salvar_json(ARQUIVO_OURO, gold)
    print(f"[Dataset] Salvo no Gold!")

class AssistenteOverlayV3(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- JANELA PRINCIPAL ---
        self.title("Translator Overlay V3")
        self.geometry("900x600")
        self.attributes("-topmost", True) # Sempre no topo
        self.attributes("-alpha", 0.96)   # Leve transparência
        ctk.set_appearance_mode("Dark")
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1) # Coluna principal expande
        self.grid_rowconfigure(0, weight=1)

        # --- PAINEL LATERAL (HISTÓRICO E MODO) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # --- NOVO: Seletor de Modo ---
        ctk.CTkLabel(self.sidebar, text="MODO DE OPERAÇÃO", font=("Arial", 12, "bold"), text_color="#00ff88").pack(pady=(15, 5))
        self.combo_modo = ctk.CTkComboBox(self.sidebar, values=["História (Script)", "Escolhas (Words)"], command=self.mudar_modo)
        self.combo_modo.pack(pady=5, padx=10)
        self.combo_modo.set("História (Script)")

        # --- NOVO: Seletor de Palavras Detectadas ---
        ctk.CTkLabel(self.sidebar, text="PALAVRAS NA TELA", font=("Arial", 10, "bold")).pack(pady=(15, 2))
        self.combo_palavras = ctk.CTkComboBox(self.sidebar, values=["..."], command=self.selecionar_palavra_detectada)
        self.combo_palavras.pack(pady=5, padx=10)
        # --------------------------------
        
        self.lbl_hist = ctk.CTkLabel(self.sidebar, text="HISTÓRICO (LOG)", font=("Arial", 12, "bold"))
        self.lbl_hist.pack(pady=(20, 10))
        
        self.scroll_hist = ctk.CTkScrollableFrame(self.sidebar, width=180)
        self.scroll_hist.pack(fill="both", expand=True, padx=5, pady=5)

        self.btn_undo = ctk.CTkButton(self.sidebar, text="↩ Desfazer (Undo)", fg_color="#444", command=self.acao_desfazer)
        self.btn_undo.pack(pady=10, padx=10, side="bottom")

        # --- ÁREA PRINCIPAL ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # 1. Info Bar
        self.info_frame = ctk.CTkFrame(self.main_area, height=40)
        self.info_frame.pack(fill="x", pady=(0, 10))
        self.lbl_status = ctk.CTkLabel(self.info_frame, text="Aguardando jogo...", font=("Consolas", 12))
        self.lbl_status.pack(side="left", padx=10)
        self.lbl_loading = ctk.CTkLabel(self.info_frame, text="", text_color="yellow")
        self.lbl_loading.pack(side="right", padx=10)

        # 2. Textos (Original vs Atual)
        self.texto_frame = ctk.CTkFrame(self.main_area)
        self.texto_frame.pack(fill="x", pady=(0, 10))
        
        # Original
        self.lbl_orig = ctk.CTkLabel(self.texto_frame, text="ORIGINAL (EN):", font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_orig.pack(anchor="w", padx=5)
        self.txt_orig = ctk.CTkTextbox(self.texto_frame, height=50, fg_color="#2b2b2b", text_color="#aaa")
        self.txt_orig.pack(fill="x", padx=5, pady=(0, 5))
        
        # Tradução Atual
        self.lbl_trad = ctk.CTkLabel(self.texto_frame, text="TRADUÇÃO ATUAL (PT):", font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_trad.pack(anchor="w", padx=5)
        self.txt_trad = ctk.CTkTextbox(self.texto_frame, height=50, font=("Arial", 14))
        self.txt_trad.pack(fill="x", padx=5, pady=(0, 5))

        # 3. Opções da IA (Radio Buttons)
        self.opcoes_frame = ctk.CTkFrame(self.main_area)
        self.opcoes_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.var_opcao = tk.IntVar(value=0)
        self.radios = []
        self.textos_opcoes = {} # Guarda os textos das opções

        for i in range(4):
            r = ctk.CTkRadioButton(self.opcoes_frame, text=f"Opção {i+1}", variable=self.var_opcao, value=i+1, command=self.selecionar_opcao)
            r.pack(anchor="w", padx=10, pady=5)
            self.radios.append(r)
            
        # Explicação da IA
        self.lbl_motivo = ctk.CTkLabel(self.opcoes_frame, text="", text_color="#aaa", wraplength=400, justify="left")
        self.lbl_motivo.pack(fill="x", padx=10, pady=5)

        # 4. Botões de Comando
        self.cmd_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.cmd_frame.pack(fill="x", side="bottom")

        self.btn_analisar = ctk.CTkButton(self.cmd_frame, text="🧠 Analisar & Gerar 4 Opções", command=self.acao_analisar, fg_color="#5a20b5", height=40)
        self.btn_analisar.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_aplicar = ctk.CTkButton(self.cmd_frame, text="✅ Aplicar Seleção (+5 Linhas)", command=self.acao_aplicar, fg_color="green", height=40)
        self.btn_aplicar.pack(side="right", fill="x", expand=True, padx=5)

        # --- ESTADO ---
        self.modo_atual = "script" 
        self.historico_acoes = []
        self.dados_visuais = {}
        self.script_memoria = []
        self.linha_idx_atual = -1
        self.monitorando = True
        self.lista_palavras_detectadas = [] 

        # SISTEMA DE FILA (Rate Limiter)
        self.fila_api = queue.Queue()
        threading.Thread(target=self.worker_processa_fila, daemon=True).start()

        # Inicia Monitor
        threading.Thread(target=self.thread_monitor, daemon=True).start()

    # --- WORKER: Processa Fila de Requisições (Rate Limiter) ---
    def worker_processa_fila(self):
        """Consome pedidos da fila respeitando o limite da API (4.5s entre chamadas)"""
        while True:
            # Pega o próximo pedido (bloqueia se estiver vazia)
            tarefa = self.fila_api.get()
            funcao_ia, args, callback_sucesso = tarefa
            
            sucesso = False
            tentativas = 0
            
            while not sucesso and tentativas < 3:
                try:
                    # Executa a chamada da IA (funcao_ia é um callable que já captura contexto)
                    resultado = funcao_ia(*args)
                    
                    # Se deu certo, chama o callback na thread principal
                    self.after(0, callback_sucesso, resultado)
                    sucesso = True
                    
                    # PAUSA OBRIGATÓRIA (Rate Limit Free Tier)
                    time.sleep(4.5) 
                    
                except Exception as e:
                    erro_str = str(e)
                    if "429" in erro_str:
                        print(f"⚠️ Cota excedida (429). Esfriando por 60s...")
                        self.after(0, lambda: self.lbl_loading.configure(text="⏳ Esfriando API (60s)...", text_color="orange"))
                        time.sleep(65) # Espera a cota renovar
                        tentativas += 1
                    else:
                        print(f"❌ Erro IA: {e}")
                        self.after(0, lambda: self.lbl_loading.configure(text="Erro API", text_color="red"))
                        break # Erro fatal, desiste dessa tarefa
            
            self.fila_api.task_done()
            if self.fila_api.empty():
                self.after(0, lambda: self.lbl_loading.configure(text=""))

    # --- LÓGICA DE MODO HÍBRIDO ---
    def mudar_modo(self, escolha):
        if "Script" in escolha:
            self.modo_atual = "script"
            self.lbl_orig.configure(text="ORIGINAL (DIALOGO):")
            self.lbl_status.configure(text="Modo: História (Automático)")
        else:
            self.modo_atual = "choice"
            self.lbl_orig.configure(text="BUSCAR PALAVRA (WORD):")
            self.lbl_status.configure(text="Modo: Escolhas (Manual)")
            self.txt_orig.delete("0.0", "end")
            self.txt_orig.insert("0.0", "Digite a palavra em inglês...")
            self.txt_trad.delete("0.0", "end")

    def selecionar_palavra_detectada(self, escolha):
        """Quando o usuário escolhe uma palavra da lista detectada"""
        if not escolha or escolha == "..." or escolha == "Selecione...": return
        
        # Muda para modo escolha se não estiver
        if self.modo_atual != "choice":
            self.combo_modo.set("Escolhas (Words)")
            self.mudar_modo("Escolhas (Words)")
            
        # Joga a palavra na caixa de texto original e dispara a busca
        self.txt_orig.delete("0.0", "end")
        self.txt_orig.insert("0.0", escolha)
        
        # Dispara a análise agora que o usuário escolheu explicitamente
        self.acao_analisar()

    def buscar_no_wordchoice(self, termo_ingles):
        """Busca manual no arquivo de escolhas"""
        if not os.path.exists(ARQUIVO_CHOICES):
            return -1, "Arquivo wordchoice.rpy não encontrado!"
            
        with open(ARQUIVO_CHOICES, "r", encoding="utf-8") as f:
            self.script_memoria = f.readlines()
            
        # Procura por: old "termo" (pode ter aspas variadas)
        idx = -1
        traducao = ""
        
        for i, linha in enumerate(self.script_memoria):
            # Verifica se a linha contém 'old "termo"'
            if 'old "' + termo_ingles + '"' in linha:
                # Achou! A tradução deve ser a próxima linha 'new'
                for k in range(i, min(i+5, len(self.script_memoria))):
                    l = self.script_memoria[k].strip()
                    if l.startswith('new '):
                        match = re.search(r'new "(.*)"', l)
                        if match: traducao = match.group(1)
                        idx = k
                        break
                break
        return idx, traducao

    def thread_monitor(self):
        last_mtime = 0
        while self.monitorando:
            if os.path.exists(ARQUIVO_VISUAL):
                try:
                    mtime = os.path.getmtime(ARQUIVO_VISUAL)
                    if mtime > last_mtime:
                        with open(ARQUIVO_VISUAL, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                        
                        tipo = dados.get("tipo", "dialogo")
                        
                        # --- CASO 1: É DIÁLOGO NO SCRIPT ---
                        if tipo == "dialogo":
                            id_t = dados.get('id_traducao')
                            if id_t and id_t != self.dados_visuais.get('id_traducao'):
                                self.dados_visuais = dados
                                # Se estivermos no modo script, atualiza a tela
                                if self.modo_atual == "script":
                                    self.after(0, self.carregar_cena_no_overlay)
                        
                        # --- CASO 2: É TELA DE ESCOLHAS ---
                        elif tipo == "escolha":
                            palavras = dados.get("opcoes_na_tela", [])
                            # Só atualiza se a lista de palavras mudou de verdade
                            if palavras and palavras != self.lista_palavras_detectadas:
                                self.lista_palavras_detectadas = palavras
                                # Atualiza o combo box, mas SEM disparar análise
                                self.after(0, self.atualizar_combo_palavras, palavras)
                                
                        last_mtime = mtime
                except Exception as e: 
                    print(f"Erro monitor: {e}")
            time.sleep(0.5)

    def atualizar_combo_palavras(self, lista):
        self.combo_palavras.configure(values=lista)
        if lista:
            self.combo_palavras.set("Selecione...") # Deixa neutro, aguardando escolha do usuário

    def carregar_cena_no_overlay(self):
        """Busca a linha no arquivo e atualiza a tela"""
        if not os.path.exists(ARQUIVO_SCRIPT): return
        
        with open(ARQUIVO_SCRIPT, "r", encoding="utf-8") as f:
            self.script_memoria = f.readlines()
            
        id_alvo = f"translate portuguese {self.dados_visuais.get('id_traducao')}:"
        
        # Busca a linha
        idx = -1
        original = ""
        traducao = ""
        
        for i, linha in enumerate(self.script_memoria):
            if id_alvo in linha:
                # Procura nas próximas 20 linhas
                for k in range(i, min(i+20, len(self.script_memoria))):
                    l = self.script_memoria[k].strip()
                    if l.startswith('#') and '"' in l:
                        original = l.replace('#', '').strip().strip('"')
                    elif not l.startswith('#') and '"' in l and "translate" not in l:
                        match = re.search(r'"(.*)"', l)
                        if match: traducao = match.group(1)
                        idx = k
                        break
                break
        
        self.linha_idx_atual = idx
        
        # Atualiza GUI
        self.lbl_status.configure(text=f"Falante: {self.dados_visuais.get('quem_fala')} | ID: {self.dados_visuais.get('id_traducao')}")
        self.txt_orig.delete("0.0", "end"); self.txt_orig.insert("0.0", original)
        self.txt_trad.delete("0.0", "end"); self.txt_trad.insert("0.0", traducao)
        
        # Reseta opções
        for r in self.radios: r.configure(text="...", state="disabled")
        self.lbl_motivo.configure(text="")

    # --- INTELIGÊNCIA ARTIFICIAL (4 OPÇÕES) ---
    def acao_analisar(self):
        if not API_KEY: return
        self.lbl_loading.configure(text="Analisando...", text_color="yellow")
        self.btn_analisar.configure(state="disabled")
        
        orig = self.txt_orig.get("0.0", "end").strip()
        trad = self.txt_trad.get("0.0", "end").strip()
        
        # --- LÓGICA DO MODO ESCOLHA ---
        if self.modo_atual == "choice":
            # Busca no arquivo wordchoice
            idx, atual_arquivo = self.buscar_no_wordchoice(orig)
            if idx != -1:
                self.linha_idx_atual = idx
                self.txt_trad.delete("0.0", "end")
                self.txt_trad.insert("0.0", atual_arquivo)
                trad = atual_arquivo
                # Não temos contexto visual para botões, passamos vazio
                quem = "SISTEMA"
                visual = "Menu de Escolha"
                ctx_bloco = "Contexto: O jogador deve escolher uma palavra que define um sentimento."
                info_char = ""
            else:
                self.lbl_status.configure(text="❌ Palavra não achada no arquivo!")
                # Continua para a IA traduzir mesmo que não ache no arquivo (para teste)
                quem, visual, ctx_bloco, info_char = "SISTEMA", "Menu", "", ""

        # --- LÓGICA DO MODO SCRIPT (A original) ---
        else:
            quem = self.dados_visuais.get("quem_fala")
            visual = self.dados_visuais.get("personagens_na_tela")
            
            # Contexto 10 linhas
            ctx_bloco = ""
            if self.linha_idx_atual != -1:
                inicio = max(0, self.linha_idx_atual - 5)
                fim = min(len(self.script_memoria), self.linha_idx_atual + 6)
                ctx_bloco = "".join(self.script_memoria[inicio:fim])
            
            # Identidade
            info_char = ""
            identidades = carregar_json(ARQUIVO_IDENTIDADE)
            q_id = str(quem[0]) if isinstance(quem, list) and quem else str(quem)
            if q_id in identidades:
                info_char = f"GÊNERO: {identidades[q_id]['genero']}"
        
        # Chama a Thread da IA (Funciona para ambos)
        threading.Thread(target=self.thread_gemini_opcoes, args=(orig, trad, quem, visual, info_char, ctx_bloco)).start()

    def thread_gemini_opcoes(self, orig, trad, quem, visual, info_char, ctx_bloco):
        # PROTEÇÃO: Se não tiver texto original, nem chama a API
        if not orig or len(orig.strip()) < 2:
            self.lbl_loading.configure(text="Texto muito curto/vazio", text_color="orange")
            self.btn_analisar.configure(state="normal")
            return

        try:
            self.lbl_loading.configure(text="🤖 Analisando... (Fila)", text_color="cyan")
            self.btn_analisar.configure(state="disabled")
            
            # Prepara a chamada da IA como função
            def chamar_ia():
                prompt = f"""
            Atue como Tradutor Sênior de Games (EN->PT-BR).
            
            CONTEXTO NARRATIVO (Histórico recente):
            '''
            {ctx_bloco}
            '''
            
            CENÁRIO ATUAL:
            Falante: {quem}
            Visual: {visual}
            {info_char}
            
            ALVO PARA CORRIGIR:
            EN: "{orig}"
            PT (Rascunho): "{trad}"
            
            TAREFA:
            Gere 3 traduções e depois crie uma 4ª opção "PERFEITA" combinando o melhor delas.
            Use o contexto narrativo para decidir tom e coerência.
            
            FORMATO:
            OPCAO_1: [Literal]
            OPCAO_2: [Natural]
            OPCAO_3: [Criativa]
            OPCAO_4: [A Melhor de Todas/Sintetizada]
            RECOMENDACAO: [1, 2, 3 ou 4]
            MOTIVO: [Explicação breve baseada no contexto]
            """
                return MODELO_IA.generate_content(prompt).text
            
            # Submete à fila com callback
            self.fila_api.put((chamar_ia, (), self.popular_opcoes))
            
        except Exception as e:
            print(e)
            self.lbl_loading.configure(text="Erro na fila", text_color="red")
            self.btn_analisar.configure(state="normal")

    def popular_opcoes(self, resposta_ia):
        self.textos_opcoes = {}
        recomendada = 4
        
        for i in range(1, 5):
            match = re.search(rf'OPCAO_{i}:\s*(.*)', resposta_ia, re.IGNORECASE)
            texto = match.group(1).strip() if match else "..."
            if texto.startswith('"') and texto.endswith('"'): texto = texto[1:-1]
            self.textos_opcoes[i] = texto
            self.radios[i-1].configure(text=f"[{i}] {texto[:60]}...", state="normal")
            
        rec_match = re.search(r'RECOMENDACAO:\s*(\d)', resposta_ia)
        if rec_match: recomendada = int(rec_match.group(1))
        
        expl_match = re.search(r'MOTIVO:\s*(.*)', resposta_ia, re.DOTALL)
        motivo = expl_match.group(1).strip() if expl_match else ""
        
        # Auto-seleciona a recomendada
        self.var_opcao.set(recomendada)
        self.selecionar_opcao() # Atualiza texto principal
        
        self.lbl_motivo.configure(text=f"💡 IA: {motivo}")
        self.lbl_loading.configure(text="", text_color="black")
        self.btn_analisar.configure(state="normal")

    def selecionar_opcao(self):
        idx = self.var_opcao.get()
        if idx in self.textos_opcoes:
            self.txt_trad.delete("0.0", "end")
            self.txt_trad.insert("0.0", self.textos_opcoes[idx])

    # --- SALVAR, HISTÓRICO E LOOK-AHEAD ---
    def acao_aplicar(self):
        if self.linha_idx_atual == -1: 
            messagebox.showwarning("Erro", "Linha não vinculada no arquivo!")
            return
        
        novo_texto = self.txt_trad.get("0.0", "end").strip()
        orig_texto = self.txt_orig.get("0.0", "end").strip()
        
        # 1. Salva no Arquivo
        linhas = self.script_memoria
        linha_antiga = linhas[self.linha_idx_atual]
        
        # Guarda para Undo (Agora salvamos o modo também)
        self.historico_acoes.append({
            "idx": self.linha_idx_atual,
            "texto_antigo": linha_antiga,
            "modo": self.modo_atual 
        })
        self.atualizar_log_historico(novo_texto)
        
        # --- APLICAÇÃO DIFERENCIADA ---
        arquivo_alvo = ARQUIVO_SCRIPT
        
        if self.modo_atual == "script":
            # Formato Script: indent "Texto"
            indent = linha_antiga.split('"')[0]
            texto_safe = novo_texto.replace('"', r'\"')
            linhas[self.linha_idx_atual] = f'{indent}"{texto_safe}"\n'
            arquivo_alvo = ARQUIVO_SCRIPT
            
        elif self.modo_atual == "choice":
            # Formato Choice: indent new "Texto"
            # Precisamos manter a indentação antes do 'new'
            indent = linha_antiga.split('new')[0]
            texto_safe = novo_texto.replace('"', r'\"')
            linhas[self.linha_idx_atual] = f'{indent}new "{texto_safe}"\n'
            arquivo_alvo = ARQUIVO_CHOICES

        with open(arquivo_alvo, "w", encoding="utf-8") as f:
            f.writelines(linhas)
            
        # 2. SALVA NO DATASET
        threading.Thread(target=aprender_traducao_logica, args=(orig_texto, novo_texto)).start()
            
        # 3. Look-Ahead (Só faz sentido no modo script)
        if self.modo_atual == "script":
            threading.Thread(target=self.thread_lookahead, args=(self.linha_idx_atual,)).start()
        
        messagebox.showinfo("Sucesso", "Alteração aplicada!")

    def thread_lookahead(self, idx_base):
        """Corrige as próximas 5 linhas no background via fila"""
        self.lbl_loading.configure(text="Look-Ahead: Verificando próximas...", text_color="cyan")
        
        try:
            # Pega as próximas 5 linhas de diálogo
            count = 0
            offset = 1
            linhas_futuras = []
            
            # Releitura fresca do arquivo para garantir índices
            if os.path.exists(ARQUIVO_SCRIPT):
                lines = open(ARQUIVO_SCRIPT, "r", encoding="utf-8").readlines()
            else:
                return
            
            while count < 5 and (idx_base + offset) < len(lines):
                idx_f = idx_base + offset
                l = lines[idx_f]
                # Verifica se é linha de diálogo traduzível
                if not l.strip().startswith('#') and '"' in l and "translate" not in l:
                    # Tenta achar o original nos comentários anteriores
                    orig_futuro = None
                    for k in range(idx_f-1, max(-1, idx_f-10), -1):
                        l_com = lines[k].strip()
                        if l_com.startswith('#') and '"' in l_com:
                            orig_futuro = l_com.replace('#', '').strip().strip('"')
                            break
                    
                    if orig_futuro:
                         linhas_futuras.append((idx_f, l, orig_futuro))
                         count += 1
                offset += 1
                
            # Processa cada linha futura via FILA
            for idx, linha_atual, original_en in linhas_futuras:
                match = re.search(r'"(.*)"', linha_atual)
                if not match: continue
                
                texto_pt_atual = match.group(1)
                
                # Se for cópia ou vazio, forçamos correção. Se já tem texto, validamos.
                # Captura as variáveis em closure para callback
                def criar_callback(o, p, i):
                    def processar_resultado(res):
                        res = res.replace("**", "").replace('"', '')
                        if res != "OK" and res != p and len(res) > 2:
                            print(f"[LookAhead] Corrigindo L{i}: {p[:10]}... -> {res[:10]}...")
                            
                            # 1. Atualiza Arquivo
                            if os.path.exists(ARQUIVO_SCRIPT):
                                lines = open(ARQUIVO_SCRIPT, "r", encoding="utf-8").readlines()
                                indent = lines[i].split('"')[0]
                                novo_pt_safe = res.replace('"', r'\"')
                                lines[i] = f'{indent}"{novo_pt_safe}"\n'
                                
                                with open(ARQUIVO_SCRIPT, "w", encoding="utf-8") as f:
                                    f.writelines(lines)
                            
                            # 2. Salva no Dataset (Aprendizado Automático)
                            threading.Thread(target=aprender_traducao_logica, args=(o, res)).start()
                    
                    return processar_resultado
                
                # Prepara a chamada da IA com os contextos capturados
                def chamar_ia_lookahead(original, atual):
                    def ia():
                        prompt = f"""
Original: "{original}"
Atual: "{atual}"
Corrija para PT-BR se necessário. Se estiver bom, responda OK.
Senão, responda apenas a frase corrigida.
                        """
                        return MODELO_IA.generate_content(prompt).text.strip()
                    return ia
                
                # Submete à fila com callback customizado
                callback = criar_callback(original_en, texto_pt_atual, idx)
                self.fila_api.put((chamar_ia_lookahead(original_en, texto_pt_atual), (), callback))

            self.lbl_loading.configure(text="Look-Ahead Concluído.", text_color="green")
            self.after(3000, lambda: self.lbl_loading.configure(text=""))
            
        except Exception as e:
            print(f"Erro LookAhead: {e}")
            self.lbl_loading.configure(text="Erro LookAhead", text_color="orange")

    def acao_desfazer(self):
        if not self.historico_acoes: return
        
        acao = self.historico_acoes.pop()
        idx = acao["idx"]
        txt_velho = acao["texto_antigo"]
        modo_antigo = acao.get("modo", "script") # Default script para compatibilidade
        
        arquivo = ARQUIVO_SCRIPT if modo_antigo == "script" else ARQUIVO_CHOICES
        
        if os.path.exists(arquivo):
            lines = open(arquivo, "r", encoding="utf-8").readlines()
            lines[idx] = txt_velho
            with open(arquivo, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            self.lbl_loading.configure(text="Desfeito!", text_color="orange")
            
            # Se for script e estivermos na mesma linha, atualiza a tela
            if modo_antigo == "script" and idx == self.linha_idx_atual:
                 self.carregar_cena_no_overlay()

    def atualizar_log_historico(self, texto_novo):
        item = ctk.CTkLabel(self.scroll_hist, text=f"📝 {texto_novo[:20]}...", anchor="w")
        item.pack(fill="x")

if __name__ == "__main__":
    app = AssistenteOverlayV3()
    app.mainloop()
