import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel
import numpy as np

# --- CONFIGURAÇÃO ---
CAMINHO_SEU_MODELO = "./modelo_annie_v1"

def iniciar_sistema():
    print("--- Carregando Músculo (Seu Tradutor)... ---")
    tokenizer = AutoTokenizer.from_pretrained(CAMINHO_SEU_MODELO)
    model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_SEU_MODELO)
    
    print("--- Carregando Consciência (O Crítico QE)... ---")
    # Usa o modelo multilingue que já baixou
    critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
    
    return tokenizer, model, critico

def traduzir_e_avaliar(texto_en, tokenizer, model, critico):
    # 1. O Músculo Traduz
    inputs = tokenizer(">>pt<< " + texto_en, return_tensors="pt", padding=True)
    translated_tokens = model.generate(**inputs, max_length=128, num_beams=5)
    traducao = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    
    # 2. O Crítico Avalia
    previsoes, score_bruto = critico.predict([[texto_en, traducao]])
    
    # --- CORREÇÃO DO ERRO 0-DIMENSIONAL ---
    # Transforma o resultado (seja array ou número) em um float simples
    valor_nota = float(score_bruto)
    
    qualidade = valor_nota * 100 
    
    return traducao, qualidade

def main():
    try:
        tokenizer, model, critico = iniciar_sistema()
    except Exception as e:
        print(f"Erro ao iniciar: {e}")
        return
    
    print("\n--- SISTEMA DE TRADUÇÃO AUTO-CONSCIENTE ---")
    print("Digite uma frase. O sistema vai traduzir e dizer o quanto confia nela.\n")

    while True:
        try:
            original = input("\nInglês: ")
            if original.lower() in ['sair', 'exit']: break
            
            traducao, confianca = traduzir_e_avaliar(original, tokenizer, model, critico)
            
            print(f"Tradução: {traducao}")
            
            # Feedback Visual
            if confianca > 70:
                status = "✅ CONFIÁVEL"
            elif confianca > 40:
                status = "⚠️ DUVIDOSO"
            else:
                status = "❌ REJEITADO"
                
            print(f"Confiança do Crítico: {confianca:.2f}% [{status}]")
            print("-" * 30)
        except Exception as e:
            print(f"Erro na execução: {e}")

if __name__ == "__main__":
    main()
