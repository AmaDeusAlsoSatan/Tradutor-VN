import json
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from difflib import SequenceMatcher

# CONFIG
ARQUIVO_TEMP = "temp_dados.json"
MODELO_REVERSO = "Helsinki-NLP/opus-mt-ROMANCE-en"

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

def main():
    print("\n--- ETAPA 2: AUDITORIA (Back-Translation) ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: Rode a Etapa 1 primeiro.")
        return

    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)

    print("Carregando modelo reverso...")
    tokenizer = AutoTokenizer.from_pretrained(MODELO_REVERSO)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODELO_REVERSO)

    print("Auditando...")
    for i, item in enumerate(tarefas):
        inputs = tokenizer(">>en<< " + item["pt"], return_tensors="pt", padding=True)
        out = model.generate(**inputs, max_length=128)
        back_en = tokenizer.decode(out[0], skip_special_tokens=True)
        
        item["back"] = back_en
        item["score_back"] = similaridade(item["original"].lower(), back_en.lower())
        print(f"\rProcessado: {i+1}/{len(tarefas)}", end="")

    with open(ARQUIVO_TEMP, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, indent=4)
        
    print("\nEtapa 2 Concluída.")

if __name__ == "__main__":
    main()
