import os
import re
import json
import gc
import torch
from difflib import SequenceMatcher
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script_novo_jogo.rpy" 
CAMINHO_MODELO_OFICIAL = "./modelo_annie_v1"
NOME_MODELO_REVERSO = "Helsinki-NLP/opus-mt-ROMANCE-en"
ARQUIVO_SNOWBALL = "dataset_auto_treino.json"
ARQUIVO_TEMP = "temp_processamento.json"

# Limiares
NOTA_MINIMA_QE = 75.0      
NOTA_MINIMA_BACK = 0.60    
NOTA_PARA_APRENDER = 90.0  

def limpar_memoria():
    gc.collect()
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

# --- FASE 1: EXTRAÇÃO E TRADUÇÃO (EN -> PT) ---
def fase_1_traducao():
    print("\n[FASE 1/3] Iniciando Tradutor (Annie)...")
    
    # 1. Ler o arquivo original
    if not os.path.exists(ARQUIVO_ALVO):
        print("Arquivo alvo não encontrado!")
        return None
    
    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    
    # 2. Identificar o que precisa ser traduzido
    tarefas = []
    regex_traducao = re.compile(r'^(\s*)(?:(\w+)\s+)?\"(.*)\"')
    regex_original = re.compile(r'^\s*#\s*(?:(\w+)\s+)?\"(.*)\"')
    
    buffer_original = None
    
    print("Mapeando linhas...")
    for i, linha in enumerate(linhas):
        match_orig = regex_original.match(linha)
        if match_orig:
            buffer_original = match_orig.group(2).replace(r'\n', '\n')
        
        match_trad = regex_traducao.match(linha)
        if match_trad and buffer_original:
            conteudo = match_trad.group(3)
            # Se a linha estiver vazia ou igual ao original (ainda não traduzida)
            if conteudo.strip() == "" or conteudo == buffer_original:
                tarefas.append({
                    "id": i,
                    "original": buffer_original,
                    "indentacao": match_trad.group(1),
                    "char_nome": match_trad.group(2) or ""
                })
            buffer_original = None

    if not tarefas:
        print("Nada para traduzir.")
        return None

    print(f"Total de linhas para traduzir: {len(tarefas)}")

    # 3. Carregar Modelo
    tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO_OFICIAL)
    model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO_OFICIAL)
    
    # 4. Traduzir em Lote
    print("Traduzindo...")
    for i, item in enumerate(tarefas):
        inputs = tokenizer(">>pt<< " + item["original"], return_tensors="pt", padding=True)
        outputs = model.generate(**inputs, max_length=128, num_beams=2) # Beam 2 para ser leve
        traducao = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        item["traducao_pt"] = traducao
        print(f"\rProgresso F1: {i+1}/{len(tarefas)}", end="", flush=True)
    
    print("\nFase 1 concluída. Liberando memória...")
    del model
    del tokenizer
    limpar_memoria()
    
    return tarefas, linhas

# --- FASE 2: AUDITORIA (PT -> EN) ---
def fase_2_back_translation(tarefas):
    print("\n[FASE 2/3] Iniciando Auditor Reverso (Helsinki)...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(NOME_MODELO_REVERSO)
        model = AutoModelForSeq2SeqLM.from_pretrained(NOME_MODELO_REVERSO)
    except:
        print("Erro ao carregar modelo reverso.")
        return tarefas

    print("Auditando (Back-Translation)...")
    for i, item in enumerate(tarefas):
        texto_pt = item["traducao_pt"]
        inputs = tokenizer(">>en<< " + texto_pt, return_tensors="pt", padding=True)
        outputs = model.generate(**inputs, max_length=128)
        back_en = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        item["back_en"] = back_en
        # Já calcula similaridade aqui para adiantar
        item["score_back"] = similaridade(item["original"].lower(), back_en.lower())
        
        print(f"\rProgresso F2: {i+1}/{len(tarefas)}", end="", flush=True)

    print("\nFase 2 concluída. Liberando memória...")
    del model
    del tokenizer
    limpar_memoria()
    return tarefas

# --- FASE 3: JULGAMENTO E SALVAMENTO ---
def fase_3_julgamento(tarefas, linhas_originais):
    print("\n[FASE 3/3] Iniciando Juiz (TransQuest)...")
    
    critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
    
    novos_aprendizados = []
    
    print("Julgando qualidade...")
    for i, item in enumerate(tarefas):
        # TransQuest
        _, score_qe = critico.predict([[item["original"], item["traducao_pt"]]])
        nota_qe = float(score_qe) * 100
        
        # Fórmula Final
        score_back_pct = item["score_back"] * 100
        nota_final = (nota_qe * 0.6) + (score_back_pct * 0.4)
        
        # Decisão
        status = "⚠️"
        if nota_final >= NOTA_PARA_APRENDER:
            status = "🌟"
            novos_aprendizados.append({"en": item["original"], "pt": item["traducao_pt"]})
        elif nota_final >= NOTA_MINIMA_QE:
            status = "✅"
            
        # Preparar linha final
        trad_safe = item["traducao_pt"].replace('\n', r'\n').replace('"', r'\"')
        prefixo = f"{item['char_nome']} " if item['char_nome'] else ""
        nova_linha_texto = f'{item["indentacao"]}{prefixo}"{trad_safe}"\n'
        
        # Inserir na lista original de linhas
        linhas_originais[item["id"]] = nova_linha_texto
        
        print(f"\rProgresso F3: {i+1}/{len(tarefas)} [{status}]", end="", flush=True)

    # Salvar Arquivo do Jogo
    print(f"\nSalvando '{ARQUIVO_ALVO}'...")
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(linhas_originais)
        
    # Salvar Aprendizado (Snowball)
    if novos_aprendizados:
        print(f"Salvando {len(novos_aprendizados)} novos itens no cérebro...")
        lista_atual = []
        if os.path.exists(ARQUIVO_SNOWBALL):
            with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
                try: lista_atual = json.load(f)
                except: pass
        
        # Adicionar sem duplicatas
        for novo in novos_aprendizados:
            if not any(d['en'] == novo['en'] for d in lista_atual):
                lista_atual.append(novo)
                
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista_atual, f, indent=4, ensure_ascii=False)

    print("\n--- PROCESSO FINALIZADO COM SUCESSO ---")

def main():
    # 1. Traduzir
    res = fase_1_traducao()
    if not res: return
    tarefas, linhas = res
    
    # 2. Auditar (Ida e Volta)
    tarefas = fase_2_back_translation(tarefas)
    
    # 3. Julgar e Gravar
    fase_3_julgamento(tarefas, linhas)

if __name__ == "__main__":
    main()
