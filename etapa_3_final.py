import json
import os
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# CONFIG
ARQUIVO_ALVO = "script_novo_jogo.rpy"
ARQUIVO_TEMP = "temp_dados.json"
ARQUIVO_SNOWBALL = "dataset_auto_treino.json"

# Limiares
NOTA_APRENDER = 90.0
NOTA_ACEITAR = 75.0

def main():
    print("\n--- ETAPA 3: JULGAMENTO FINAL ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: Rode as etapas anteriores.")
        return

    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)
        
    print("Carregando Juiz (TransQuest)...")
    critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
    
    novos_aprendizados = []
    
    print("Julgando...")
    for i, item in enumerate(tarefas):
        # AQUI O SEGREDO: Previsão unitária e limpa
        _, score_qe = critico.predict([[item["original"], item["pt"]]])
        nota_qe = float(score_qe) * 100
        
        score_back_pct = item["score_back"] * 100
        nota_final = (nota_qe * 0.6) + (score_back_pct * 0.4)
        
        item["nota_final"] = nota_final
        
        if nota_final >= NOTA_APRENDER:
            novos_aprendizados.append({"en": item["original"], "pt": item["pt"]})
            
        print(f"\rL{item['id']}: {nota_final:.1f}%", end="")

    # Escrever no arquivo RPY
    print("\nEscrevendo arquivo final...")
    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        
    for item in tarefas:
        trad_safe = item["pt"].replace('\n', r'\n').replace('"', r'\"')
        prefixo = f"{item['char']} " if item['char'] else ""
        nova_linha = f'{item["indent"]}{prefixo}"{trad_safe}"\n'
        linhas[item["id"]] = nova_linha
        
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(linhas)
        
    # Salvar Snowball
    if novos_aprendizados:
        lista = []
        if os.path.exists(ARQUIVO_SNOWBALL):
            with open(ARQUIVO_SNOWBALL, "r", encoding="utf-8") as f:
                try: lista = json.load(f)
                except: pass
        
        for novo in novos_aprendizados:
            if not any(d['en'] == novo['en'] for d in lista):
                lista.append(novo)
                
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=4, ensure_ascii=False)
            
    print(f"\n\nSUCESSO TOTAL! {len(novos_aprendizados)} novas frases aprendidas.")
    os.remove(ARQUIVO_TEMP) # Limpa a bagunça

if __name__ == "__main__":
    main()
