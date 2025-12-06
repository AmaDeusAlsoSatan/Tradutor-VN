import customtkinter as ctk
import json
import os
import threading
import time
import re
from dotenv import load_dotenv
import google.generativeai as genai
from tkinter import messagebox

# --- CONFIGURAÇÕES ---
# SEU CAMINHO (Mantenha o que estava funcionando)
PASTA_BASE_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc" 
ARQUIVO_VISUAL = os.path.join(PASTA_BASE_JOGO, "game", "estado_visual.json")
ARQUIVO_SCRIPT = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "script.rpy")

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"
ARQUIVO_IDENTIDADE = "identidade.json"

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configura IA (Com fallback)
if API_KEY:
    genai.configure(api_key=API_KEY)
    try:
        MODELO_IA = genai.GenerativeModel('models/gemini-2.0-flash')
    except:
        MODELO_IA = genai.GenerativeModel('models/gemini-pro')

class AssistenteOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Assistente VN - Overlay V2")
        self.geometry("600x450")
        self.attributes("-topmost", True) 
        self.attributes("-alpha", 0.95)   
        ctk.set_appearance_mode("Dark")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Barra de Status
        self.frame_info = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a")
        self.frame_info.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.lbl_id = ctk.CTkLabel(self.frame_info, text="ID: ...", font=("Consolas", 11), text_color="#aaaaaa")
        self.lbl_id.pack(side="left", padx=10)

        self.lbl_personagem = ctk.CTkLabel(self.frame_info, text="...", font=("Arial", 14, "bold"), text_color="#00ff88")
        self.lbl_personagem.pack(side="left", padx=10)
        
        self.lbl_visual = ctk.CTkLabel(self.frame_info, text="Aguardando conexão...", font=("Arial", 12))
        self.lbl_visual.pack(side="right", padx=10)

        # 2. Área de Texto
        self.frame_texto = ctk.CTkFrame(self)
        self.frame_texto.grid(row=1, column=0, sticky="nsew", padx=5)
        
        self.lbl_orig = ctk.CTkLabel(self.frame_texto, text="Original (EN):", text_color="gray", anchor="w")
        self.lbl_orig.pack(fill="x", padx=5)
        self.txt_orig = ctk.CTkTextbox(self.frame_texto, height=70, text_color="#aaaaaa")
        self.txt_orig.pack(fill="x", padx=5, pady=(0, 5))
        
        self.lbl_trad = ctk.CTkLabel(self.frame_texto, text="Tradução (PT):", text_color="gray", anchor="w")
        self.lbl_trad.pack(fill="x", padx=5)
        self.txt_trad = ctk.CTkTextbox(self.frame_texto, height=70, text_color="white", font=("Arial", 14))
        self.txt_trad.pack(fill="x", padx=5, pady=(0, 5))

        # 3. Botões
        self.frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botoes.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.btn_ia = ctk.CTkButton(self.frame_botoes, text="✨ Auto-Fix (IA)", command=self.acao_ia_fix, fg_color="#5a20b5")
        self.btn_ia.pack(side="left", expand=True, fill="x", padx=2)
        
        self.btn_salvar = ctk.CTkButton(self.frame_botoes, text="💾 Salvar Manual", command=self.acao_salvar_manual, fg_color="green")
        self.btn_salvar.pack(side="right", expand=True, fill="x", padx=2)

        # Estado
        self.dados_atuais = {}
        self.script_completo = []
        self.linha_script_idx = -1
        
        self.monitorando = True
        threading.Thread(target=self.loop_espião, daemon=True).start()

    def loop_espião(self):
        """Monitora o arquivo JSON e atualiza por ID"""
        last_mtime = 0
        while self.monitorando:
            if os.path.exists(ARQUIVO_VISUAL):
                try:
                    mtime = os.path.getmtime(ARQUIVO_VISUAL)
                    if mtime > last_mtime:
                        with open(ARQUIVO_VISUAL, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                        
                        id_atual = dados.get('id_traducao')
                        if id_atual and id_atual != self.dados_atuais.get('id_traducao'):
                            self.dados_atuais = dados
                            # SÓ ATUALIZA SE ACHAR O ID NO SCRIPT
                            self.after(0, self.buscar_e_atualizar, id_atual)
                            last_mtime = mtime
                except Exception as e:
                    print(f"Erro leitura: {e}")
            time.sleep(0.5)

    def carregar_script_memoria(self):
        if os.path.exists(ARQUIVO_SCRIPT):
            with open(ARQUIVO_SCRIPT, "r", encoding="utf-8") as f:
                self.script_completo = f.readlines()
        return self.script_completo

    def buscar_e_atualizar(self, id_traducao):
        """Busca a linha no arquivo pelo ID do RenPy (Infalível)"""
        self.carregar_script_memoria()
        
        # O ID no arquivo aparece como: translate portuguese ID_DA_LINHA:
        tag_busca = f"translate portuguese {id_traducao}:"
        
        idx_encontrado = -1
        original = "Original não encontrado"
        traducao_atual = ""
        
        for i, linha in enumerate(self.script_completo):
            if tag_busca in linha:
                # Achamos o bloco! Agora vamos procurar a tradução logo abaixo
                # Geralmente:
                # i: translate...
                # i+1: vazio ou comentário
                # ...
                # i+n: linha com aspas (tradução)
                
                # Varre as próximas 20 linhas procurando o par
                for k in range(i, min(i + 20, len(self.script_completo))):
                    l_check = self.script_completo[k].strip()
                    
                    # Se for comentário com aspas, é o original
                    if l_check.startswith('#') and '"' in l_check:
                        original = l_check.replace('#', '').strip()
                        if original.startswith('"') and original.endswith('"'):
                            original = original[1:-1]
                            
                    # Se for linha de código com aspas, é a tradução
                    elif not l_check.startswith('#') and '"' in l_check and "translate" not in l_check:
                        idx_encontrado = k
                        match = re.search(r'"(.*)"', l_check)
                        if match:
                            traducao_atual = match.group(1)
                        # Se achou a tradução, paramos de procurar neste bloco
                        break
                break
        
        self.linha_script_idx = idx_encontrado
        
        # Atualiza a Interface
        self.lbl_id.configure(text=f"ID: {id_traducao}")
        
        quem = self.dados_atuais.get("quem_fala", "")
        if isinstance(quem, list): quem = " ".join(quem)
        self.lbl_personagem.configure(text=str(quem).upper() if quem else "NARRADOR")
        
        visual = self.dados_atuais.get("personagens_na_tela", [])
        self.lbl_visual.configure(text=f"Visual: {len(visual)} sprites")

        self.txt_orig.delete("0.0", "end")
        self.txt_orig.insert("0.0", original)
        
        self.txt_trad.delete("0.0", "end")
        self.txt_trad.insert("0.0", traducao_atual)

    def acao_ia_fix(self):
        if not API_KEY:
            messagebox.showerror("Erro", "Sem chave API no .env")
            return
            
        if self.linha_script_idx == -1:
            messagebox.showwarning("Aviso", "Linha não encontrada no script!")
            return

        original = self.txt_orig.get("0.0", "end").strip()
        atual = self.txt_trad.get("0.0", "end").strip()
        quem = self.lbl_personagem.cget("text")
        visual = str(self.dados_atuais.get("personagens_na_tela", []))
        
        self.btn_ia.configure(text="Pensando...", state="disabled")
        threading.Thread(target=self.thread_ia, args=(original, atual, quem, visual)).start()

    def thread_ia(self, original, atual, quem, visual):
        try:
            prompt = f"""
            Contexto Visual: {visual}
            Falante: {quem}
            Original EN: "{original}"
            Tradução PT: "{atual}"
            
            Tarefa: Corrija a tradução para PT-BR.
            - Respeite Gênero (Feminino/Masculino) baseado no nome e contexto.
            - Respeite Número (Singular/Plural) baseado na quantidade de pessoas no visual.
            - Retorne APENAS a frase corrigida, sem explicações.
            """
            res = MODELO_IA.generate_content(prompt).text.strip()
            
            # Limpeza
            res = res.replace("**", "")
            if res.startswith('"') and res.endswith('"'): res = res[1:-1]
            match_renpy = re.match(r'^.+?\s+"(.*)"$', res)
            if match_renpy: res = match_renpy.group(1)
            
            self.txt_trad.delete("0.0", "end")
            self.txt_trad.insert("0.0", res)
            self.btn_ia.configure(text="✨ Auto-Fix (IA)", state="normal")
            
        except Exception as e:
            print(e)
            self.btn_ia.configure(text="Erro IA", state="normal")

    def acao_salvar_manual(self):
        if self.linha_script_idx == -1: return
        
        nova_traducao = self.txt_trad.get("0.0", "end").strip()
        
        # Lê o arquivo fresco
        linhas = self.carregar_script_memoria()
        linha_antiga = linhas[self.linha_script_idx]
        
        # Preserva indentação e quem fala (ex: "    m ")
        prefixo = linha_antiga.split('"')[0]
        
        # Escapa aspas internas
        conteudo_safe = nova_traducao.replace('"', r'\"')
        
        # Monta a nova linha
        nova_linha = f'{prefixo}"{conteudo_safe}"\n'
        linhas[self.linha_script_idx] = nova_linha
        
        with open(ARQUIVO_SCRIPT, "w", encoding="utf-8") as f:
            f.writelines(linhas)
            
        self.btn_salvar.configure(text="Salvo! (Shift+R)", fg_color="gray")
        self.after(2000, lambda: self.btn_salvar.configure(text="💾 Salvar Manual", fg_color="green"))

if __name__ == "__main__":
    app = AssistenteOverlay()
    app.mainloop()