import json
import os
import gc
import torch
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÃO ---
ARQUIVO_ALVO = "script.rpy"
ARQUIVO_TEMP = "temp_dados.json"
ARQUIVO_SNOWBALL = "dataset_auto_treino.json"

# Configurações de Engenharia
TAMANHO_LOTE = 8  # Processa 8 frases por vez (Seguro para pouca RAM)
NOTA_APRENDER = 90.0

def limpar_memoria():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def main():
    print("\n--- ETAPA 3: JULGAMENTO EM LOTE (V4 Otimizado) ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: Rode a Etapa 1 e 2 primeiro.")
        return

    # 1. Carregar Dados
    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)
    
    print(f"Carregando Juiz (TransQuest) para avaliar {len(tarefas)} linhas...")
    try:
        critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
    except Exception as e:
        print(f"Erro ao carregar o Juiz: {e}")
        return

    novos_aprendizados = []
    
    # 2. Preparar Pares para Avaliação
    # O TransQuest adora listas de pares [[orig, trad], [orig, trad]...]
    todos_pares = [[t['original'], t['pt']] for t in tarefas]
    
    # 3. Processar em Lotes (Batches)
    print(f"Iniciando avaliação em pacotes de {TAMANHO_LOTE}...")
    
    todas_notas = []
    total = len(todos_pares)
    
    for i in range(0, total, TAMANHO_LOTE):
        lote_atual = todos_pares[i : i + TAMANHO_LOTE]
        
        # O Juiz avalia o pacote inteiro de uma vez
        # predict retorna (predições, notas_brutas)
        _, notas_lote = critico.predict(lote_atual)
        
        # Converte para lista Python simples se vier como tensor/numpy
        if hasattr(notas_lote, 'tolist'):
            notas_lote = notas_lote.tolist()
            
        todas_notas.extend(notas_lote)
        
        # Feedback visual e limpeza
        print(f"\rProcessado: {min(i + TAMANHO_LOTE, total)}/{total}", end="")
        limpar_memoria()

    print("\n\nConsolidando resultados...")

    # 4. Aplicar Notas e Regras de Negócio
    for i, item in enumerate(tarefas):
        nota_qe = float(todas_notas[i]) * 100
        score_back_pct = item.get("score_back", 0) * 100
        
        # Média Ponderada (60% Fluência, 40% Fidelidade)
        nota_final = (nota_qe * 0.6) + (score_back_pct * 0.4)
        item["nota_final"] = nota_final
        
        # Lógica de Aprendizado (O "Snowball")
        if nota_final >= NOTA_APRENDER:
            novos_aprendizados.append({"en": item["original"], "pt": item["pt"]})

    # 5. Escrever no Arquivo Final (Injeção Cirúrgica)
    print(f"Escrevendo traduções em '{ARQUIVO_ALVO}'...")
    if os.path.exists(ARQUIVO_ALVO):
        with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
            linhas_arquivo = f.readlines()
            
        injecoes = 0
        for item in tarefas:
            idx = item.get('line_index')
            # Segurança contra índice inválido
            if idx is not None and idx < len(linhas_arquivo):
                trad_safe = item["pt"].replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{item['char']} " if item['char'] else ""
                
                # Mantém a indentação original
                nova_linha = f'{item["indent"]}{prefixo}"{trad_safe}"\n'
                linhas_arquivo[idx] = nova_linha
                injecoes += 1
        
        with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
            f.writelines(linhas_arquivo)
    else:
        print("Aviso: Arquivo script.rpy original não encontrado para injeção.")

    # 6. Salvar Aprendizado
    if novos_aprendizados:
        print(f"🧠 CÉREBRO: {len(novos_aprendizados)} novas frases mestre aprendidas!")
        lista = []
        if os.path.exists(ARQUIVO_SNOWBALL):
            with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
                try: lista = json.load(f)
                except: pass
        
        # Evita duplicatas
        originais = {d['en'] for d in lista}
        for novo in novos_aprendizados:
            if novo['en'] not in originais:
                lista.append(novo)
                
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=4, ensure_ascii=False)
            
    print(f"Processo finalizado. {len(tarefas)} linhas processadas.")

if __name__ == "__main__":
    main()
