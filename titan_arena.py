"""TITAN: Arena de Tradução - GUI semi-automática
Cria uma interface para comparar Annie (local) vs serviços web e salvar decisões
no `dataset_snowball.json`. Imports opcionais são tratados para permitir edição
do arquivo mesmo em máquinas sem todas as dependências instaladas.
"""
import os
import json
import re
import time
import threading
import subprocess
import logging
import sys
from datetime import datetime

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

import pandas as pd

# Import de bibliotecas de IA/serviços com guards
try:
    import g4f
    G4F_AVAILABLE = True
except Exception:
    G4F_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    DEEP_AVAILABLE = True
except Exception:
    DEEP_AVAILABLE = False

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSeq2SeqLM,
        AutoModelForSequenceClassification,
    )
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# Juiz (TransQuest) - modelo predefinido
MODELO_JUIZ = "TransQuest/monotransquest-da-multilingual"
JUDGE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)


# --- Configurações visuais padrão quando possível ---
if TK_AVAILABLE:
    try:
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
    except Exception:
        pass


class TagManager:
    """Gerencia a proteção de tags (ex: {i}, \n, comandos)."""
    def __init__(self):
        self.mapa = {}
        self.contador = 0
        # Regex para capturar tags frequentes usadas em VN/Translator++
        self.padrao = re.compile(r'({.*?}|\\n|\\[a-zA-Z]+\[.*?\]|\\[a-zA-Z]+|<.*?>|\[.*?\])')

    def mascarar(self, texto):
        self.mapa = {}
        self.contador = 0

        def substituir(match):
            token = f"__T{self.contador}__"
            self.mapa[token] = match.group(0)
            self.contador += 1
            return token

        return self.padrao.sub(substituir, texto)

    def desmascarar(self, texto_traduzido):
        for token, tag in self.mapa.items():
            # Use callable replacement to avoid 'bad escape' when tag contains backslashes
            texto_traduzido = re.sub(rf'\s*{token}\s*', (lambda m, t=tag: t), texto_traduzido, flags=re.IGNORECASE)
        return texto_traduzido


class TitanEngine:
    """Motor responsável por Annie (local) e serviços web (com fallbacks)."""
    def __init__(self, caminho_annie="./modelo_annie_v1"):
        self.annie_model = None
        self.annie_tokenizer = None
        self.juiz_model = None
        self.juiz_tokenizer = None
        self.caminho_annie = caminho_annie
        if TRANSFORMERS_AVAILABLE:
            self.carregar_annie()
            # tentativa preguiçosa de carregar juiz será feita sob demanda

    def carregar_annie(self):
        try:
            if os.path.exists(self.caminho_annie):
                self.annie_tokenizer = AutoTokenizer.from_pretrained(self.caminho_annie)
                self.annie_model = AutoModelForSeq2SeqLM.from_pretrained(self.caminho_annie)
                print("Annie carregada com sucesso!")
            else:
                print("Annie não encontrada na pasta local.")
        except Exception as e:
            print(f"Erro ao carregar Annie: {e}")

    def traduzir_annie(self, texto):
        if not TRANSFORMERS_AVAILABLE or not self.annie_model:
            return "Erro: Annie offline ou transformers não instalado"
        try:
            # Força token >>pt<< para reduzir vazamento em espanhol
            inp = f">>pt<< {texto}"
            inputs = self.annie_tokenizer(inp, return_tensors="pt", padding=True, truncation=True)
            out = self.annie_model.generate(**inputs, max_length=512, num_beams=4)
            return self.annie_tokenizer.decode(out[0], skip_special_tokens=True)
        except Exception as e:
            return f"Erro Annie: {e}"

    def traduzir_google_web(self, texto):
        if not DEEP_AVAILABLE:
            return "Erro Google: deep-translator não instalado"
        try:
            return GoogleTranslator(source='auto', target='pt').translate(texto)
        except Exception as e:
            return f"Erro Google: {e}"

    def traduzir_gpt_web(self, texto, contexto_extra=""):
        if not G4F_AVAILABLE:
            return "Erro GPT Web: g4f não instalado"
        try:
            prompt = f"Translate the following text to Portuguese (Brazil). Maintain the style suitable for a Game/Novel. Context: {contexto_extra}\n\nText: {texto}"
            # Tenta selecionar um nome de modelo presente no pacote g4f.models
            model_candidate = None
            try:
                models_module = getattr(g4f, 'models', None)
                if models_module is not None:
                    # tenta alguns nomes comuns
                    for attr in ('gpt_35_turbo', 'gpt_3_5_turbo', 'gpt_3_5', 'gpt', 'chatgpt', 'gpt4'):
                        if hasattr(models_module, attr):
                            model_candidate = getattr(models_module, attr)
                            break
            except Exception:
                model_candidate = None

            # fallback para string de nome do modelo se não encontrar atributo
            if model_candidate is None:
                model_candidate = 'gpt-3.5-turbo'

            err = None
            try:
                response = g4f.ChatCompletion.create(
                    model=model_candidate,
                    messages=[{"role": "user", "content": prompt}],
                )
            except AttributeError:
                # Algumas versões de g4f aceitam 'model' como str e outras usam constants
                try:
                    response = g4f.ChatCompletion.create(
                        messages=[{"role": "user", "content": prompt}],
                    )
                except Exception as e:
                    err = e
                    response = None
            except Exception as e:
                err = e
                response = None

            # Se g4f falhou, tenta fallback para Google (se disponível)
            if response is None or (isinstance(response, str) and ("Model not found" in str(response) or str(response).lower().startswith('erro'))):
                if DEEP_AVAILABLE:
                    try:
                        gt = GoogleTranslator(source='auto', target='pt').translate(texto)
                        # marca que foi fallback
                        return f"[Fallback: Google] {gt}"
                    except Exception as e:
                        return f"Erro GPT Web (g4f falhou): {err or e}"
                return f"Erro GPT Web (g4f falhou): {err}"

            return response
        except Exception as e:
            return f"Erro GPT Web: {e}"

    def carregar_juiz(self):
        global JUDGE_AVAILABLE
        if not TRANSFORMERS_AVAILABLE:
            return False
        try:
            # Carrega tokenizer/model do TransQuest (pode demorar e exigir protobuf compatível)
            self.juiz_tokenizer = AutoTokenizer.from_pretrained(MODELO_JUIZ)
            self.juiz_model = AutoModelForSequenceClassification.from_pretrained(MODELO_JUIZ)
            JUDGE_AVAILABLE = True
            logging.info("Juiz TransQuest carregado")
            return True
        except Exception as e:
            logging.warning(f"Não foi possível carregar Juiz TransQuest: {e}")
            JUDGE_AVAILABLE = False
            return False

    def avaliar_judge(self, original, traducao):
        """Retorna um score entre 0.0 e 1.0 usando TransQuest quando disponível,
        ou uma heurística simples quando não.
        """
        # Tenta carregar juiz sob demanda
        if not JUDGE_AVAILABLE and TRANSFORMERS_AVAILABLE:
            self.carregar_juiz()

        if JUDGE_AVAILABLE and self.juiz_model:
            try:
                # Prepara input simples: concat original + translation
                text = original + " [SEP] " + traducao
                inputs = self.juiz_tokenizer(text, return_tensors="pt", truncation=True)
                out = self.juiz_model(**inputs)
                logits = out.logits.detach()
                # If logits is single-dim regression (shape [1,1]), apply sigmoid
                try:
                    import torch
                    if logits.ndim == 2 and logits.shape[1] == 1:
                        score = float(torch.sigmoid(logits)[0, 0])
                        return max(0.0, min(1.0, score))
                    else:
                        scores = logits.softmax(dim=-1)
                        score = float(scores[0, 1])
                        return max(0.0, min(1.0, score))
                except Exception:
                    try:
                        scores = logits.softmax(dim=-1)
                        score = float(scores[0, 1])
                        return max(0.0, min(1.0, score))
                    except Exception:
                        pass
            except Exception as e:
                logging.warning(f"Erro ao avaliar com juiz: {e}")

        # Heurística: overlap token básico
        try:
            s1 = set(re.findall(r"\w+", original.lower()))
            s2 = set(re.findall(r"\w+", traducao.lower()))
            if not s1:
                return 0.5
            overlap = len(s1 & s2) / max(1, len(s1))
            # escala para 0.3-0.95
            return float(max(0.0, min(1.0, 0.3 + 0.65 * overlap)))
        except Exception:
            return 0.5


if TK_AVAILABLE:
    class TitanApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("TITAN: Arena de Tradução - Projeto VN")
            self.geometry("1200x800")

            self.engine = TitanEngine()
            self.tag_manager = TagManager()
            self.df_contexto = None
            self.historico_arquivo = "historico_titan.json"

            self.criar_interface()

        def criar_interface(self):
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)

            # Sidebar
            self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
            self.sidebar.grid(row=0, column=0, sticky="nsew")

            ctk.CTkLabel(self.sidebar, text="CONTEXTO (XLSX)", font=("Arial", 16, "bold")).pack(pady=10)
            self.btn_load_xlsx = ctk.CTkButton(self.sidebar, text="Carregar Map/Script.xlsx", command=self.carregar_xlsx)
            self.btn_load_xlsx.pack(pady=5, padx=10)

            # Juiz (TransQuest) controls
            self.btn_load_juiz = ctk.CTkButton(self.sidebar, text="Carregar Juiz (TransQuest)", command=self.thread_load_juiz)
            self.btn_load_juiz.pack(pady=5, padx=10)
            self.lbl_juiz_status = ctk.CTkLabel(self.sidebar, text="Juiz: Desconectado", text_color="orange")
            self.lbl_juiz_status.pack(pady=2)

            self.lbl_contexto_prev = ctk.CTkTextbox(self.sidebar, height=150, text_color="gray")
            self.lbl_contexto_prev.pack(pady=5, padx=5, fill="x")
            self.lbl_contexto_prev.insert("0.0", "Carregue um XLSX para ver as linhas anteriores...")

            ctk.CTkLabel(self.sidebar, text="Linha Atual (Contexto)", font=("Arial", 12)).pack()
            self.lbl_contexto_next = ctk.CTkTextbox(self.sidebar, height=150, text_color="gray")
            self.lbl_contexto_next.pack(pady=5, padx=5, fill="x")
            self.lbl_contexto_next.insert("0.0", "Linhas futuras aparecerão aqui...")

            # Main area
            self.main_area = ctk.CTkFrame(self, corner_radius=0)
            self.main_area.grid(row=0, column=1, sticky="nsew")

            ctk.CTkLabel(self.main_area, text="TEXTO ORIGINAL (Inglês)", anchor="w").pack(fill="x", padx=20, pady=(20,0))
            self.txt_original = ctk.CTkTextbox(self.main_area, height=80)
            self.txt_original.pack(fill="x", padx=20, pady=5)

            self.frame_botoes = ctk.CTkFrame(self.main_area, fg_color="transparent")
            self.frame_botoes.pack(fill="x", padx=20, pady=5)

            self.btn_traduzir = ctk.CTkButton(self.frame_botoes, text="⚔️ INICIAR ARENA ⚔️", command=self.iniciar_arena, fg_color="green")
            self.btn_traduzir.pack(side="left", padx=5)

            self.check_limite = ctk.CTkCheckBox(self.frame_botoes, text="Respeitar Limite de Caracteres")
            self.check_limite.pack(side="left", padx=10)

            # Treinador automático
            self.lbl_epochs = ctk.CTkLabel(self.frame_botoes, text="Epochs:")
            self.lbl_epochs.pack(side="left", padx=(10,2))
            self.entry_epochs = ctk.CTkEntry(self.frame_botoes, width=60)
            self.entry_epochs.insert(0, "3")
            self.entry_epochs.pack(side="left", padx=(0,5))
            self.btn_train = ctk.CTkButton(self.frame_botoes, text="⏫ Treinar Annie", fg_color="orange", command=self.thread_run_trainer)
            self.btn_train.pack(side="left", padx=5)

            ctk.CTkLabel(self.main_area, text="RESULTADOS DA COMPETIÇÃO", anchor="w").pack(fill="x", padx=20, pady=(10,0))
            self.scroll_arena = ctk.CTkScrollableFrame(self.main_area, height=300)
            self.scroll_arena.pack(fill="x", padx=20, pady=5)

            ctk.CTkLabel(self.main_area, text="TRADUÇÃO FINAL (Sua Escolha)", anchor="w").pack(fill="x", padx=20, pady=(10,0))
            self.txt_final = ctk.CTkTextbox(self.main_area, height=80, border_color="green", border_width=2)
            self.txt_final.pack(fill="x", padx=20, pady=5)

            self.lbl_status_tamanho = ctk.CTkLabel(self.main_area, text="Tamanho: 0 / 0", text_color="gray")
            self.lbl_status_tamanho.pack(anchor="e", padx=20)

            self.btn_salvar = ctk.CTkButton(self.main_area, text="💾 SALVAR E TREINAR ANNIE", command=self.salvar_decisao)
            self.btn_salvar.pack(pady=10)

            # Área de log de treinamento
            self.txt_train_log = ctk.CTkTextbox(self.main_area, height=120)
            self.txt_train_log.pack(fill="x", padx=20, pady=(0,10))

        def carregar_xlsx(self):
            filename = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.csv")])
            if filename:
                try:
                    if filename.endswith('.csv'):
                        self.df_contexto = pd.read_csv(filename)
                    else:
                        self.df_contexto = pd.read_excel(filename)

                    if 'Original Text' in self.df_contexto.columns:
                        self.col_orig = 'Original Text'
                    elif 'Source' in self.df_contexto.columns:
                        self.col_orig = 'Source'
                    else:
                        self.col_orig = self.df_contexto.columns[0]

                    messagebox.showinfo("Sucesso", f"Arquivo carregado! {len(self.df_contexto)} linhas.")
                except Exception as e:
                    messagebox.showerror("Erro", str(e))

        # --- Juiz loading helpers ---
        def thread_load_juiz(self):
            threading.Thread(target=self.load_juiz, daemon=True).start()

        def load_juiz(self):
            self.lbl_juiz_status.configure(text="Juiz: Carregando...", text_color="orange")
            ok = self.engine.carregar_juiz()
            if ok:
                self.lbl_juiz_status.configure(text="Juiz: Pronto", text_color="green")
            else:
                self.lbl_juiz_status.configure(text="Juiz: Falha (ver logs)", text_color="red")
                messagebox.showwarning("Juiz", "Não foi possível carregar o Juiz TransQuest. Tente instalar: protobuf==3.20.3 e verifique a internet.")

        def buscar_contexto(self, texto_busca):
            if self.df_contexto is None: return ""
            matches = self.df_contexto[self.df_contexto[self.col_orig].astype(str).str.contains(texto_busca, regex=False, na=False)]
            contexto_str = ""
            if not matches.empty:
                idx = matches.index[0]
                prev_lines = [str(self.df_contexto.iloc[i][self.col_orig]) for i in range(max(0, idx-3), idx)]
                next_lines = [str(self.df_contexto.iloc[i][self.col_orig]) for i in range(idx+1, min(len(self.df_contexto), idx+4))]
                self.lbl_contexto_prev.delete("0.0", "end")
                self.lbl_contexto_prev.insert("0.0", "\n---\n".join(prev_lines))
                self.lbl_contexto_next.delete("0.0", "end")
                self.lbl_contexto_next.insert("0.0", "\n---\n".join(next_lines))
                contexto_str = f"Previous lines: {' | '.join(prev_lines)}"
            return contexto_str

        def iniciar_arena(self):
            texto_orig = self.txt_original.get("0.0", "end").strip()
            if not texto_orig: return
            contexto_ia = self.buscar_contexto(texto_orig)
            texto_seguro = self.tag_manager.mascarar(texto_orig)
            for widget in self.scroll_arena.winfo_children():
                widget.destroy()

            servicos = [
                ("Annie (Local)", self.engine.traduzir_annie, [texto_seguro]),
                ("Google Web", self.engine.traduzir_google_web, [texto_seguro]),
                ("GPT-3.5 (Web)", self.engine.traduzir_gpt_web, [texto_seguro, contexto_ia]),
            ]

            # guarda candidatos temporariamente
            self.last_candidates = []

            for nome, func, args in servicos:
                t = threading.Thread(target=self.rodar_servico, args=(nome, func, args))
                t.start()

        def rodar_servico(self, nome, func, args):
            try:
                inicio = time.time()
                res_raw = func(*args)
                res_final = self.tag_manager.desmascarar(res_raw)
                tempo = time.time() - inicio
                # calcula score com juiz/heurística
                try:
                    score = self.engine.avaliar_judge(self.txt_original.get("0.0", "end").strip(), res_final)
                except Exception:
                    score = 0.5
                # salva candidato
                self.last_candidates.append({"servico": nome, "texto": res_final, "score": float(score)})
                self.adicionar_resultado_arena(nome, res_final, tempo, score)
            except Exception as e:
                self.adicionar_resultado_arena(nome, f"Erro: {e}", 0, 0.0)

        def adicionar_resultado_arena(self, nome, texto, tempo, score=0.0):
            frame = ctk.CTkFrame(self.scroll_arena)
            frame.pack(fill="x", pady=5)
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x")
            ctk.CTkLabel(header, text=f"{nome} ({tempo:.1f}s)", font=("Arial", 12, "bold")).pack(side="left", padx=5)
            ctk.CTkLabel(header, text=f"Score: {score:.2f}", text_color="yellow").pack(side="left", padx=6)
            btn_usar = ctk.CTkButton(header, text="Usar Esta", width=80, height=20, command=lambda t=texto: self.selecionar_traducao(t))
            btn_usar.pack(side="right", padx=5)
            msg = ctk.CTkTextbox(frame, height=50)
            msg.insert("0.0", texto)
            msg.configure(state="disabled")
            msg.pack(fill="x", padx=5, pady=5)

        def selecionar_traducao(self, texto):
            self.txt_final.delete("0.0", "end")
            self.txt_final.insert("0.0", texto)
            self.verificar_tamanho()

        def verificar_tamanho(self):
            orig = self.txt_original.get("0.0", "end").strip()
            trad = self.txt_final.get("0.0", "end").strip()
            len_o = len(orig)
            len_t = len(trad)
            cor = "gray"
            obs = ""
            if self.check_limite.get():
                limite = len_o * 1.2
                if len_t > limite:
                    cor = "red"
                    obs = " (MUITO LONGO!)"
                elif len_t < len_o * 0.5:
                    cor = "orange"
                    obs = " (Muito curto?)"
                else:
                    cor = "green"
            self.lbl_status_tamanho.configure(text=f"Original: {len_o} | Tradução: {len_t}{obs}", text_color=cor)

        def salvar_decisao(self):
            original = self.txt_original.get("0.0", "end").strip()
            escolhida = self.txt_final.get("0.0", "end").strip()
            if not original or not escolhida:
                return
            dataset_entry = {
                "source": original,
                "target": escolhida,
                "timestamp": datetime.now().isoformat(),
                "origin": "Titan_Manual",
                "candidates": getattr(self, 'last_candidates', [])
            }
            arquivo_treino = "dataset_snowball.json"
            lista_treino = []
            if os.path.exists(arquivo_treino):
                with open(arquivo_treino, "r", encoding="utf-8") as f:
                    try:
                        lista_treino = json.load(f)
                    except Exception:
                        pass
            lista_treino.append(dataset_entry)
            with open(arquivo_treino, "w", encoding="utf-8") as f:
                json.dump(lista_treino, f, indent=4, ensure_ascii=False)

            # Salva histórico completo (entrada + candidatos + chosen)
            hist = []
            if os.path.exists(self.historico_arquivo):
                try:
                    with open(self.historico_arquivo, "r", encoding="utf-8") as f:
                        hist = json.load(f)
                except Exception:
                    hist = []
            hist_entry = {
                "timestamp": datetime.now().isoformat(),
                "source": original,
                "chosen": escolhida,
                "candidates": getattr(self, 'last_candidates', [])
            }
            hist.append(hist_entry)
            with open(self.historico_arquivo, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=4, ensure_ascii=False)

            # Limpa UI
            self.txt_original.delete("0.0", "end")
            self.txt_final.delete("0.0", "end")
            for w in self.scroll_arena.winfo_children():
                w.destroy()
            messagebox.showinfo("Salvo", "Tradução salva, histórico atualizado e adicionada ao dataset de treino!")

        # ---------------- Trainer Integration ----------------
        def thread_run_trainer(self):
            try:
                epochs = int(self.entry_epochs.get())
            except Exception:
                epochs = 3
            threading.Thread(target=self.run_trainer, args=(epochs,), daemon=True).start()

        def run_trainer(self, epochs=3):
            """Chama `treinador_nmt.py --dataset dataset_snowball.json --epochs N` e
            escreve o log na caixa de texto `txt_train_log`.
            """
            cmd = [sys.executable, "treinador_nmt.py", "--dataset", "dataset_snowball.json", "--epochs", str(epochs)]
            self.txt_train_log.insert("0.0", f"Iniciando treino: {' '.join(cmd)}\n")
            self.txt_train_log.see("end")
            # Desabilita botão de treino enquanto roda
            try:
                self.btn_train.configure(state="disabled")
            except Exception:
                pass
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self.txt_train_log.insert("end", line)
                    self.txt_train_log.see("end")
                proc.wait()
                self.txt_train_log.insert("end", f"Treino finalizado com código {proc.returncode}\n")
                self.txt_train_log.see("end")
            except Exception as e:
                self.txt_train_log.insert("end", f"Erro ao executar treinador: {e}\n")
                self.txt_train_log.see("end")
            finally:
                try:
                    self.btn_train.configure(state="normal")
                except Exception:
                    pass
                messagebox.showinfo("Treino", "Processo de treino finalizado. Verifique o log.")



def smoke_test_headless():
    print('TITAN smoke test (headless)')
    tm = TagManager()
    s = 'Hello {i} world\nNew line and \\layer_test[1]'
    m = tm.mascarar(s)
    print('Masked:', m)
    um = tm.desmascarar(m)
    print('Unmasked snippet:', um[:80])
    eng = TitanEngine()
    print('Annie test:', eng.traduzir_annie('This is a test'))
    print('Juiz score example:', eng.avaliar_judge('Hello', 'Olá'))


if __name__ == "__main__":
    if '--smoke' in sys.argv:
        smoke_test_headless()
    elif not TK_AVAILABLE:
        print("A biblioteca customtkinter não está instalada. Instale-a para rodar a GUI:\n    pip install customtkinter")
    else:
        app = TitanApp()
        app.mainloop()
