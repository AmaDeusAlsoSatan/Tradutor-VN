import os
import re
import json
import gc # Garbage Collector para limpar memória
from difflib import SequenceMatcher
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script_novo_jogo.rpy" 
CAMINHO_MODELO_OFICIAL = "./modelo_annie_v1"
NOME_MODELO_REVERSO = "Helsinki-NLP/opus-mt-ROMANCE-en"
ARQUIVO_SNOWBALL = "dataset_auto_treino.json"

# Limiares
NOTA_MINIMA_QE = 75.0      
NOTA_MINIMA_BACK = 0.60    
NOTA_PARA_APRENDER = 90.0  

print("--- INICIANDO BETA TESTER V2 (LITE) ---")

print("[1/4] Carregando Tradutor Oficial...")
tokenizer_oficial = AutoTokenizer.from_pretrained(CAMINHO_MODELO_OFICIAL)
model_oficial = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO_OFICIAL)

print("[2/4] Carregando Auditor Reverso...")
tokenizer_back = AutoTokenizer.from_pretrained(NOME_MODELO_REVERSO)
model_back = AutoModelForSeq2SeqLM.from_pretrained(NOME_MODELO_REVERSO)

print("[3/4] Carregando Crítico (Juiz)...")
critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)

memoria_sessao = {}
if os.path.exists(ARQUIVO_SNOWBALL):
    with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
        try:
            dados_antigos = json.load(f)
            for par in dados_antigos:
                memoria_sessao[par['en']] = par['pt']
        except: pass

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

def back_translation_check(texto_pt):
    inputs = tokenizer_back(">>en<< " + texto_pt, return_tensors="pt", padding=True)
    translated = model_back.generate(**inputs, max_length=128)
    return tokenizer_back.decode(translated[0], skip_special_tokens=True)

def traduzir_linha_unica(texto_original):
    # Memória
    if texto_original in memoria_sessao:
        return memoria_sessao[texto_original], 100.0, "MEMORIA"

    # Tradução (Gera apenas 1 opção para economizar RAM)
    inputs = tokenizer_oficial(">>pt<< " + texto_original, return_tensors="pt", padding=True)
    outputs = model_oficial.generate(**inputs, max_length=128, num_beams=4) # Beam 4 é um bom equilíbrio
    candidato = tokenizer_oficial.decode(outputs[0], skip_special_tokens=True)

    # Verificações
    if candidato.strip() == texto_original.strip() or not candidato:
        return candidato, 0.0, "Cópia/Vazio"

    # Back Translation
    volta = back_translation_check(candidato)
    score_back = similaridade(texto_original.lower(), volta.lower())
    
    if score_back < NOTA_MINIMA_BACK:
        return candidato, score_back * 100, f"Falha Contexto ({score_back:.2f})"

    # TransQuest
    _, score_qe = critico.predict([[texto_original, candidato]])
    nota_qe = float(score_qe) * 100

    # Média Final
    score_final = (nota_qe * 0.6) + (score_back * 100 * 0.4)
    log = f"QE:{nota_qe:.0f}|Back:{score_back:.2f}"
    
    return candidato, score_final, log

def salvar_aprendizado(original, traducao):
    novo = {"en": original, "pt": traducao}
    lista = []
    if os.path.exists(ARQUIVO_SNOWBALL):
        with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
            try: lista = json.load(f)
            except: pass
    
    if not any(d['en'] == original for d in lista):
        lista.append(novo)
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=4, ensure_ascii=False)
        memoria_sessao[original] = traducao

def processar_arquivo():
    if not os.path.exists(ARQUIVO_ALVO):
        print(f"Erro: '{ARQUIVO_ALVO}' não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    regex_traducao = re.compile(r'^(\s*)(?:(\w+)\s+)?\"(.*)\"')
    regex_original = re.compile(r'^\s*#\s*(?:(\w+)\s+)?\"(.*)\"')
    
    buffer_original = None
    contador_novos = 0

    print(f"\n--- Iniciando Tradução Segura: {ARQUIVO_ALVO} ---")

    for i, linha in enumerate(linhas):
        match_orig = regex_original.match(linha)
        if match_orig:
            buffer_original = match_orig.group(2).replace(r'\n', '\n')
        
        match_trad = regex_traducao.match(linha)
        if match_trad and buffer_original:
            indentacao = match_trad.group(1)
            char_nome = match_trad.group(2) or ""
            conteudo = match_trad.group(3)

            if conteudo.strip() == "" or conteudo == buffer_original:
                # Print FLUSH=True garante que o texto apareça antes de travar
                print(f"L{i}: Traduzindo '{buffer_original[:20]}...' -> ", end="", flush=True)
                
                traducao, score, log = traduzir_linha_unica(buffer_original)
                
                icon = "❓"
                if score >= NOTA_PARA_APRENDER:
                    icon = "🌟"
                    salvar_aprendizado(buffer_original, traducao)
                    contador_novos += 1
                elif score >= NOTA_MINIMA_QE:
                    icon = "✅"
                
                print(f"{icon} ({log})")
                
                trad_safe = traducao.replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{char_nome} " if char_nome else ""
                novas_linhas.append(f'{indentacao}{prefixo}"{trad_safe}"\n')
                
                # LIMPEZA DE MEMÓRIA (Crucial para não crashar)
                if i % 10 == 0:
                    gc.collect() 
            else:
                novas_linhas.append(linha)
            buffer_original = None
        else:
            novas_linhas.append(linha)

    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"\n--- FIM ---")
    print(f"Frases aprendidas: {contador_novos}")

if __name__ == "__main__":
    processar_arquivo()
