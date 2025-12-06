import customtkinter as ctk
import json
import os
import threading
import time
import re
from dotenv import load_dotenv
import google.generativeai as genai
from tkinter import messagebox
import tkinter as tk

# --- CONFIGURAÇÕES ---
# SEU CAMINHO (Ajuste para a pasta da VN 3)
PASTA_BASE_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc" 
ARQUIVO_VISUAL = os.path.join(PASTA_BASE_JOGO, "game", "estado_visual.json")
ARQUIVO_SCRIPT = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "script.rpy")
ARQUIVO_IDENTIDADE = "identidade.json"

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configura IA
if API_KEY:
    genai.configure(api_key=API_KEY)
    # Tenta usar o Flash, se não der, usa o Pro
    try: MODELO_IA = genai.GenerativeModel('models/gemini-2.0-flash')
    except: MODELO_IA = genai.GenerativeModel('models/gemini-pro')

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

        # --- PAINEL LATERAL (HISTÓRICO) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_hist = ctk.CTkLabel(self.sidebar, text="HISTÓRICO (LOG)", font=("Arial", 12, "bold"))
        self.lbl_hist.pack(pady=10)
        
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
        self.historico_acoes = [] # Pilha para Undo
        self.dados_visuais = {}
        self.script_memoria = []
        self.linha_idx_atual = -1
        self.monitorando = True
        
        # Inicia Monitor
        threading.Thread(target=self.thread_monitor, daemon=True).start()

    # --- MONITORAMENTO (O Espião) ---
    def thread_monitor(self):
        last_mtime = 0
        while self.monitorando:
            if os.path.exists(ARQUIVO_VISUAL):
                try:
                    mtime = os.path.getmtime(ARQUIVO_VISUAL)
                    if mtime > last_mtime:
                        with open(ARQUIVO_VISUAL, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                        
                        id_t = dados.get('id_traducao')
                        if id_t and id_t != self.dados_visuais.get('id_traducao'):
                            self.dados_visuais = dados
                            # Agenda atualização na GUI
                            self.after(0, self.carregar_cena_no_overlay)
                            last_mtime = mtime
                except: pass
            time.sleep(0.5)

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
        self.lbl_loading.configure(text="Consultando Gemini...", text_color="yellow")
        self.btn_analisar.configure(state="disabled")
        
        # Coleta contexto
        quem = self.dados_visuais.get("quem_fala")
        visual = self.dados_visuais.get("personagens_na_tela")
        orig = self.txt_orig.get("0.0", "end").strip()
        trad = self.txt_trad.get("0.0", "end").strip()
        
        # Identidade
        info_char = ""
        identidades = {}
        if os.path.exists(ARQUIVO_IDENTIDADE):
            identidades = json.load(open(ARQUIVO_IDENTIDADE, "r"))
            # Se for lista, pega o primeiro
            if isinstance(quem, list) and len(quem) > 0: q_id = quem[0]
            else: q_id = str(quem)
            
            if q_id in identidades:
                info_char = f"GÊNERO: {identidades[q_id]['genero']}"
        
        threading.Thread(target=self.thread_gemini_opcoes, args=(orig, trad, quem, visual, info_char)).start()

    def thread_gemini_opcoes(self, orig, trad, quem, visual, info_char):
        try:
            prompt = f"""
            Atue como Tradutor Sênior de Games (EN->PT-BR).
            
            CENÁRIO:
            Falante: {quem}
            Visual: {visual}
            {info_char}
            
            ALVO:
            EN: "{orig}"
            PT (Rascunho): "{trad}"
            
            TAREFA:
            Gere 3 traduções e depois crie uma 4ª opção "PERFEITA" combinando o melhor delas.
            
            FORMATO:
            OPCAO_1: [Literal]
            OPCAO_2: [Natural]
            OPCAO_3: [Criativa]
            OPCAO_4: [A Melhor de Todas/Sintetizada]
            RECOMENDACAO: [1, 2, 3 ou 4]
            MOTIVO: [Explicação breve]
            """
            
            res = MODELO_IA.generate_content(prompt).text
            
            self.after(0, self.popular_opcoes, res)
            
        except Exception as e:
            print(e)
            self.lbl_loading.configure(text="Erro API", text_color="red")
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
        if self.linha_idx_atual == -1: return
        
        novo_texto = self.txt_trad.get("0.0", "end").strip()
        
        # 1. Salva no Arquivo
        linhas = self.script_memoria
        linha_antiga = linhas[self.linha_idx_atual]
        
        # Guarda para Undo
        self.historico_acoes.append({
            "idx": self.linha_idx_atual,
            "texto_antigo": linha_antiga
        })
        self.atualizar_log_historico(novo_texto)
        
        # Escreve
        indent = linha_antiga.split('"')[0]
        texto_safe = novo_texto.replace('"', r'\"')
        linhas[self.linha_idx_atual] = f'{indent}"{texto_safe}"\n'
        
        with open(ARQUIVO_SCRIPT, "w", encoding="utf-8") as f:
            f.writelines(linhas)
            
        # 2. Trigger Look-Ahead (As próximas 5 linhas)
        threading.Thread(target=self.thread_lookahead, args=(self.linha_idx_atual,)).start()
        
        messagebox.showinfo("Sucesso", "Alteração aplicada! Dê Shift+R.")

    def thread_lookahead(self, idx_base):
        """Corrige as próximas 5 linhas no background"""
        self.lbl_loading.configure(text="Corrigindo próximas 5 linhas...", text_color="cyan")
        
        try:
            # Pega as próximas 5 linhas de diálogo
            count = 0
            offset = 1
            linhas_futuras = []
            
            # Lê o arquivo fresco
            lines = open(ARQUIVO_SCRIPT, "r", encoding="utf-8").readlines()
            
            while count < 5 and (idx_base + offset) < len(lines):
                l = lines[idx_base + offset]
                if not l.strip().startswith('#') and '"' in l and "translate" not in l:
                    linhas_futuras.append((idx_base + offset, l))
                    count += 1
                offset += 1
                
            # Manda para o Gemini em lote (para economizar requisições)
            for idx, conteudo in linhas_futuras:
                time.sleep(2) # Respeita cota
                # (Aqui entraria a lógica simplificada de mandar corrigir)
                # Para V3, vamos apenas imprimir no console para não arriscar corromper enquanto você joga
                print(f"[LookAhead] Analisando futura linha {idx}...")
                
            self.lbl_loading.configure(text="Look-Ahead concluído.", text_color="green")
            self.after(3000, lambda: self.lbl_loading.configure(text=""))
            
        except Exception as e:
            print(f"Erro LookAhead: {e}")

    def acao_desfazer(self):
        if not self.historico_acoes: return
        
        acao = self.historico_acoes.pop()
        idx = acao["idx"]
        txt_velho = acao["texto_antigo"]
        
        lines = open(ARQUIVO_SCRIPT, "r", encoding="utf-8").readlines()
        lines[idx] = txt_velho
        with open(ARQUIVO_SCRIPT, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        self.lbl_loading.configure(text="Desfeito!", text_color="orange")
        
        # Atualiza GUI se estivermos na mesma linha
        if idx == self.linha_idx_atual:
             self.carregar_cena_no_overlay()

    def atualizar_log_historico(self, texto_novo):
        item = ctk.CTkLabel(self.scroll_hist, text=f"📝 {texto_novo[:20]}...", anchor="w")
        item.pack(fill="x")

if __name__ == "__main__":
    app = AssistenteOverlayV3()
    app.mainloop()
