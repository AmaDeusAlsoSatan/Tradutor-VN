import os
import re
import json
import torch
from difflib import SequenceMatcher
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script_novo_jogo.rpy"  # Arquivo que vamos traduzir
CAMINHO_MODELO_OFICIAL = "./modelo_annie_v1" # Seu modelo treinado (EN -> PT)
NOME_MODELO_REVERSO = "Helsinki-NLP/opus-mt-ROMANCE-en" # Modelo Reverso (PT -> EN) para o teste
ARQUIVO_SNOWBALL = "dataset_auto_treino.json" # Onde ele guarda o que aprendeu sozinho

# Limiares de Rigidez (Ajuste se for muito chato)
NOTA_MINIMA_QE = 75.0      # Nota do TransQuest para aceitar a frase
NOTA_MINIMA_BACK = 0.60    # Similaridade (0.0 a 1.0) do inglês original vs inglês que voltou
NOTA_PARA_APRENDER = 90.0  # Nota para confiar cegamente e salvar no dataset de treino

print("--- INICIANDO O BETA TESTER MATEMÁTICO ---")

# 1. Carregar o Músculo (EN -> PT)
print("[1/4] Carregando Tradutor Oficial...")
tokenizer_oficial = AutoTokenizer.from_pretrained(CAMINHO_MODELO_OFICIAL)
model_oficial = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO_OFICIAL)

# 2. Carregar o Auditor (PT -> EN)
print("[2/4] Carregando Modelo de Back-Translation (Auditoria)...")
try:
    tokenizer_back = AutoTokenizer.from_pretrained(NOME_MODELO_REVERSO)
    model_back = AutoModelForSeq2SeqLM.from_pretrained(NOME_MODELO_REVERSO)
except Exception as e:
    print(f"\nERRO: Você precisa baixar o modelo reverso '{NOME_MODELO_REVERSO}' primeiro.")
    print("O script vai baixar automaticamente na primeira vez, garanta internet conectada.")
    exit()

# 3. Carregar o Juiz (TransQuest)
print("[3/4] Carregando Crítico de Qualidade...")
critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)

# 4. Memória Rápida (Para não traduzir a mesma coisa duas vezes erradas)
memoria_sessao = {}
if os.path.exists(ARQUIVO_SNOWBALL):
    with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
        dados_antigos = json.load(f)
        for par in dados_antigos:
            memoria_sessao[par['en']] = par['pt']
print(f"[4/4] Sistema Pronto. Memória carregada: {len(memoria_sessao)} itens.")

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

def back_translation_check(texto_pt):
    """Traduz do PT de volta para o EN para ver se o sentido se manteve."""
    inputs = tokenizer_back(">>en<< " + texto_pt, return_tensors="pt", padding=True)
    translated = model_back.generate(**inputs, max_length=128)
    texto_en_volta = tokenizer_back.decode(translated[0], skip_special_tokens=True)
    return texto_en_volta

def traduzir_com_auditoria(texto_original):
    # Checagem de Memória (Já aprendi isso hoje?)
    if texto_original in memoria_sessao:
        return memoria_sessao[texto_original], 100.0, "MEMORIA"

    # Geração de Candidatos (Beam Search - Gera 3 opções)
    inputs = tokenizer_oficial(">>pt<< " + texto_original, return_tensors="pt", padding=True)
    outputs = model_oficial.generate(**inputs, max_length=128, num_beams=5, num_return_sequences=3)
    candidatos = [tokenizer_oficial.decode(t, skip_special_tokens=True) for t in outputs]

    melhor_traducao = candidatos[0]
    melhor_score_final = -1
    log_decisao = "Falha"

    # O "Beta Tester" analisa cada candidato
    for cand in candidatos:
        # PORTÃO 1: Sanidade Lógica
        if cand.strip() == texto_original.strip() or len(cand) == 0:
            continue # Rejeita cópia ou vazio
        
        # PORTÃO 2: Back-Translation (Ida e Volta)
        volta = back_translation_check(cand)
        score_back = similaridade(texto_original.lower(), volta.lower())
        
        if score_back < NOTA_MINIMA_BACK:
            continue # O sentido mudou demais, rejeita

        # PORTÃO 3: TransQuest (Fluência)
        _, score_qe = critico.predict([[texto_original, cand]])
        nota_qe = float(score_qe) * 100

        # Score Ponderado (Damos muito valor se a volta for perfeita)
        score_final = (nota_qe * 0.6) + (score_back * 100 * 0.4)

        if score_final > melhor_score_final:
            melhor_score_final = score_final
            melhor_traducao = cand
            log_decisao = f"QE:{nota_qe:.1f}% | Back:{score_back:.2f}"

    return melhor_traducao, melhor_score_final, log_decisao

def salvar_aprendizado(original, traducao):
    """Salva no arquivo Snowball para o futuro fine-tuning"""
    novo_dado = {"en": original, "pt": traducao}
    
    lista_atual = []
    if os.path.exists(ARQUIVO_SNOWBALL):
        with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
            try:
                lista_atual = json.load(f)
            except: pass
    
    # Evita duplicatas
    if not any(d['en'] == original for d in lista_atual):
        lista_atual.append(novo_dado)
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista_atual, f, indent=4, ensure_ascii=False)
        # Atualiza RAM
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

    print(f"\n--- Iniciando Tradução de '{ARQUIVO_ALVO}' ---")

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
                print(f"Linha {i}: '{buffer_original[:30]}...' ", end="")
                
                traducao, score, log = traduzir_com_auditoria(buffer_original)
                
                status_icon = "❓"
                if score >= NOTA_PARA_APRENDER:
                    status_icon = "🌟 (APRENDIDO)"
                    salvar_aprendizado(buffer_original, traducao)
                    contador_novos += 1
                elif score >= NOTA_MINIMA_QE:
                    status_icon = "✅"
                else:
                    status_icon = "⚠️ (INCERTO)"
                
                print(f"-> {status_icon} [{log}]")
                
                trad_safe = traducao.replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{char_nome} " if char_nome else ""
                novas_linhas.append(f'{indentacao}{prefixo}"{trad_safe}"\n')
            else:
                novas_linhas.append(linha)
            buffer_original = None
        else:
            novas_linhas.append(linha)

    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"\n--- FIM ---")
    print(f"Novas frases aprendidas e salvas no Snowball: {contador_novos}")

if __name__ == "__main__":
    processar_arquivo()
