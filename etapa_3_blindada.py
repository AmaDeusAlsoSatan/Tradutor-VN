import json
import os
import gc
import torch
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÃO ---
ARQUIVO_ALVO = "script.rpy"
ARQUIVO_TEMP = "temp_dados.json"
ARQUIVO_CHECKPOINT = "checkpoint_juiz.json"

# Onde guardamos o conhecimento
ARQUIVO_OURO = "dataset_master_gold.json"       # Certeza absoluta (>90%)
ARQUIVO_PRATA = "dataset_incubadora_silver.json" # Bom, mas pode melhorar (70-89%)

# Critérios do PDF (Consenso)
NOTA_MASTER = 90.0
NOTA_ACEITAVEL = 70.0

def limpar_memoria():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def main():
    print("\n--- ETAPA 3: JULGAMENTO EVOLUTIVO (Consenso + Incubadora) ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: Arquivo temporário não encontrado.")
        return

    # 1. Carregar Tarefas
    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)
    
    print(f"Total de linhas para julgar: {len(tarefas)}")

    # 2. Limpar checkpoint antigo para garantir cálculo novo
    if os.path.exists(ARQUIVO_CHECKPOINT):
        try: os.remove(ARQUIVO_CHECKPOINT)
        except: pass

    print("Carregando o Juiz (TransQuest)...")
    try:
        critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
    except Exception as e:
        print(f"Erro fatal: {e}")
        return

    print("Iniciando avaliação com Lógica de Consenso...")
    
    novos_ouro = []
    novos_prata = []
    count_injecoes = 0

    # Carrega arquivo para injeção
    if os.path.exists(ARQUIVO_ALVO):
        with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
            linhas_arquivo = f.readlines()
    else:
        linhas_arquivo = []

    for i, item in enumerate(tarefas):
        
        try:
            # --- AVALIAÇÃO (O Juiz Neural) ---
            _, score_bruto = critico.predict([[item["original"], item["pt"]]])
            nota_juiz = float(score_bruto) * 100
            
            # --- AUDITORIA (O Back-Translation) ---
            score_auditor = item.get("score_back", 0) * 100
            
            # --- LÓGICA DE CONSENSO (Baseada no PDF) ---
            # Se o Auditor (fidelidade) for alto, ele dá um voto de confiança no Juiz
            if score_auditor > 80.0:
                bonus = (score_auditor - 80.0) * 0.5
                nota_final = nota_juiz + bonus
                if nota_final > 100: nota_final = 100
            else:
                nota_final = nota_juiz

            # O Porteiro (Segurança Mínima)
            if score_auditor < 20.0:
                nota_final = 0.0
                icon = "⛔"
            
            # --- CLASSIFICAÇÃO (Sua Ideia da Incubadora) ---
            aprendeu_ouro = False
            foi_prata = False

            if nota_final >= NOTA_MASTER:
                icon = "🌟 [OURO]"
                novos_ouro.append(item)
                aprendeu_ouro = True
            elif nota_final >= NOTA_ACEITAVEL:
                icon = "🥈 [PRATA]"
                novos_prata.append(item) # Salva para o futuro!
                foi_prata = True
            elif nota_final >= 60:
                icon = "✅ [OK]" # Vai pro jogo, mas não aprendemos nada
            else:
                icon = "⚠️ [RUIM]"

            print(f"\rL{item['line_index']}: J={nota_juiz:.0f}%|A={score_auditor:.0f}% -> Final={nota_final:.1f}% {icon}", end="")

            # Injeção no Jogo (Tudo que não for lixo vai para o jogo)
            if nota_final > 0 and item['line_index'] < len(linhas_arquivo):
                trad_safe = item["pt"].replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{item['char']} " if item['char'] else ""
                linhas_arquivo[item['line_index']] = f'{item["indent"]}{prefixo}"{trad_safe}"\n'
                count_injecoes += 1
            
            limpar_memoria()

        except Exception as e:
            print(f"\nErro L{item['line_index']}: {e}")
            break

    # Salvar Arquivo do Jogo
    if linhas_arquivo:
        with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
            f.writelines(linhas_arquivo)
            
    # --- GESTÃO DE CONHECIMENTO ---
    
    # 1. Salvar OURO (Aprendizado Imediato)
    if novos_ouro:
        print(f"\n\n🏆 MAESTRIA: {len(novos_ouro)} frases perfeitas para o treino imediato!")
        salvar_dataset(ARQUIVO_OURO, novos_ouro)

    # 2. Salvar PRATA (Sua Incubadora)
    if novos_prata:
        print(f"💡 INCUBADORA: {len(novos_prata)} frases boas salvas para refinar no futuro!")
        salvar_dataset(ARQUIVO_PRATA, novos_prata)

    print(f"\nProcesso finalizado. {count_injecoes} linhas injetadas no jogo.")

def salvar_dataset(nome_arquivo, novos_dados):
    lista = []
    if os.path.exists(nome_arquivo):
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            try: lista = json.load(f)
            except: pass
    
    # Evita duplicatas baseadas no original em inglês
    originais = {d['en'] if 'en' in d else d['original'] for d in lista}
    
    for item in novos_dados:
        # Padroniza o formato
        entrada = {
            "en": item["original"], 
            "pt": item["pt"],
            "score": item.get("nota_final", 0),
            "contexto_vn": "VN_Atual" # Tag para sabermos de onde veio
        }
        
        if entrada['en'] not in originais:
            lista.append(entrada)
            
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
