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
# SEU CAMINHO (Ajuste se mudou)
PASTA_BASE_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc" 
ARQUIVO_VISUAL = os.path.join(PASTA_BASE_JOGO, "game", "estado_visual.json")
ARQUIVO_SCRIPT = os.path.join(PASTA_BASE_JOGO, "game", "tl", "portuguese", "script.rpy")

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_IDENTIDADE = "identidade.json"

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configura IA
if API_KEY:
    genai.configure(api_key=API_KEY)
    MODELO_IA = genai.GenerativeModel('models/gemini-2.0-flash')

class AssistenteOverlay(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Assistente VN - Overlay")
        self.geometry("500x350")
        self.attributes("-topmost", True) # Sempre no topo
        self.attributes("-alpha", 0.95)   # Leve transparência
        ctk.set_appearance_mode("Dark")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Barra de Status (Quem fala / Visual)
        self.frame_info = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a")
        self.frame_info.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.lbl_personagem = ctk.CTkLabel(self.frame_info, text="Aguardando...", font=("Arial", 14, "bold"), text_color="#00ff88")
        self.lbl_personagem.pack(side="left", padx=10)
        
        self.lbl_visual = ctk.CTkLabel(self.frame_info, text="Cena: ???", font=("Arial", 12))
        self.lbl_visual.pack(side="right", padx=10)

        # 2. Área de Texto (Original vs Tradução)
        self.frame_texto = ctk.CTkFrame(self)
        self.frame_texto.grid(row=1, column=0, sticky="nsew", padx=5)
        
        self.lbl_orig = ctk.CTkLabel(self.frame_texto, text="Original (EN):", text_color="gray", anchor="w")
        self.lbl_orig.pack(fill="x", padx=5)
        self.txt_orig = ctk.CTkTextbox(self.frame_texto, height=60, text_color="#aaaaaa")
        self.txt_orig.pack(fill="x", padx=5, pady=(0, 5))
        
        self.lbl_trad = ctk.CTkLabel(self.frame_texto, text="Tradução (PT):", text_color="gray", anchor="w")
        self.lbl_trad.pack(fill="x", padx=5)
        self.txt_trad = ctk.CTkTextbox(self.frame_texto, height=60, text_color="white", font=("Arial", 13))
        self.txt_trad.pack(fill="x", padx=5, pady=(0, 5))

        # 3. Botões de Ação
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
        
        # Thread de Monitoramento
        self.monitorando = True
        threading.Thread(target=self.loop_espião, daemon=True).start()

    def loop_espião(self):
        """Lê o arquivo JSON do jogo a cada 0.5s"""
        last_mtime = 0
        while self.monitorando:
            if os.path.exists(ARQUIVO_VISUAL):
                try:
                    mtime = os.path.getmtime(ARQUIVO_VISUAL)
                    if mtime > last_mtime:
                        with open(ARQUIVO_VISUAL, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                        
                        # Se mudou a linha, atualiza a GUI
                        if dados.get('id_traducao') != self.dados_atuais.get('id_traducao'):
                            self.dados_atuais = dados
                            self.atualizar_gui_com_dados(dados)
                            last_mtime = mtime
                except: pass
            time.sleep(0.5)

    def carregar_script_memoria(self):
        """Lê o script.rpy para achar a linha exata"""
        if os.path.exists(ARQUIVO_SCRIPT):
            with open(ARQUIVO_SCRIPT, "r", encoding="utf-8") as f:
                self.script_completo = f.readlines()
        return self.script_completo

    def buscar_linha_no_script(self, texto_visivel):
        """Tenta achar a linha do jogo no arquivo físico"""
        self.carregar_script_memoria()
        # Busca aproximada
        for i, linha in enumerate(self.script_completo):
            if texto_visivel in linha and not linha.strip().startswith('#'):
                # Achou! Tenta pegar o original no comentário acima
                original = "???"
                for j in range(i-1, max(-1, i-10), -1):
                    l = self.script_completo[j].strip()
                    if l.startswith('#') and '"' in l:
                        original = l.replace('#', '').strip()
                        break
                return i, original
        return -1, ""

    def atualizar_gui_com_dados(self, dados):
        texto_pt = dados.get("texto_mostrado", "")
        quem = dados.get("quem_fala", "")
        if isinstance(quem, list): quem = " ".join(quem) or "Narração"
        
        visual = f"{dados.get('quantidade_pessoas', 0)} pessoas: {dados.get('personagens_na_tela', [])}"
        
        # Atualiza Labels (Precisa ser na thread principal, mas CTk lida bem)
        self.lbl_personagem.configure(text=quem.upper())
        self.lbl_visual.configure(text=visual)
        
        # Busca no script físico para pegar o original
        idx, original = self.buscar_linha_no_script(texto_pt)
        self.linha_script_idx = idx
        
        self.txt_trad.delete("0.0", "end")
        self.txt_trad.insert("0.0", texto_pt)
        
        self.txt_orig.delete("0.0", "end")
        self.txt_orig.insert("0.0", original)

    def acao_ia_fix(self):
        if not API_KEY:
            messagebox.showerror("Erro", "Sem chave API no .env")
            return
            
        if self.linha_script_idx == -1:
            messagebox.showwarning("Aviso", "Não achei essa linha no arquivo script.rpy!")
            return

        # Pega dados da GUI
        original = self.txt_orig.get("0.0", "end").strip()
        atual = self.txt_trad.get("0.0", "end").strip()
        quem = self.lbl_personagem.cget("text")
        visual = self.lbl_visual.cget("text")
        
        # Chama Gemini
        self.btn_ia.configure(text="Pensando...", state="disabled")
        threading.Thread(target=self.thread_ia, args=(original, atual, quem, visual)).start()

    def thread_ia(self, original, atual, quem, visual):
        try:
            prompt = f"""
            Contexto Visual: {visual}
            Falante: {quem}
            Original EN: "{original}"
            Tradução PT: "{atual}"
            
            Tarefa: Corrija a tradução considerando Gênero e Número (ex: Bem-vindo vs Bem-vinda).
            Retorne APENAS a frase corrigida.
            """
            res = MODELO_IA.generate_content(prompt).text.strip()
            if res.startswith('"'): res = res[1:-1]
            
            # Atualiza GUI
            self.txt_trad.delete("0.0", "end")
            self.txt_trad.insert("0.0", res)
            self.btn_ia.configure(text="✨ Auto-Fix (IA)", state="normal")
            
            # Auto-Salvar? Ou esperar o usuário clicar?
            # Vamos esperar o usuário confirmar no botão verde.
            
        except Exception as e:
            print(e)
            self.btn_ia.configure(text="Erro IA", state="normal")

    def acao_salvar_manual(self):
        if self.linha_script_idx == -1: return
        
        nova_traducao = self.txt_trad.get("0.0", "end").strip()
        
        # Salva no arquivo
        linhas = self.carregar_script_memoria()
        indent = linhas[self.linha_script_idx].split('"')[0]
        
        if '"' in nova_traducao: nova_traducao = nova_traducao.replace('"', r'\"')
        linhas[self.linha_script_idx] = f'{indent}"{nova_traducao}"\n'
        
        with open(ARQUIVO_SCRIPT, "w", encoding="utf-8") as f:
            f.writelines(linhas)
            
        # Feedback Visual
        self.btn_salvar.configure(text="Salvo! (Shift+R)", fg_color="gray")
        self.after(2000, lambda: self.btn_salvar.configure(text="💾 Salvar Manual", fg_color="green"))
        
        # Salva no Ouro (Lógica simplificada)
        # (Pode adicionar a função aprender_traducao aqui depois)

if __name__ == "__main__":
    app = AssistenteOverlay()
    app.mainloop()