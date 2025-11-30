import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÕES ---
CAMINHO_MODELO_TREINADO = "./modelo_annie_v1"
ARQUIVO_ENTRADA = "script_nova_vn.txt" # Você usará isso na próxima VN
ARQUIVO_SAIDA = "traducao_final.txt"

print("--- INICIANDO A ENGINE DE TRADUÇÃO HÍBRIDA ---")

# 1. Carregar o Músculo (Seu Modelo)
print("[1/3] Carregando Modelo Neural Personalizado...")
try:
    tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO_TREINADO)
    model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO_TREINADO)
except Exception as e:
    print(f"Erro fatal: {e}")
    print("Você rodou o 'treinador_nmt.py'? A pasta do modelo existe?")
    exit()

# 2. Carregar a Consciência (O Crítico)
print("[2/3] Carregando o Crítico de Qualidade (TransQuest)...")
try:
    critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)
except Exception as e:
    print(f"Erro ao carregar crítico: {e}")
    exit()

def filtro_sanidade(original, traducao):
    """Regras lógicas para impedir erros estúpidos da IA"""
    # Regra 1: O "Paradoxo do Gibberish"
    # Se a tradução for igual ao original e tiver mais de 4 letras, provavelmente a IA desistiu.
    if original.strip() == traducao.strip() and len(original) > 4:
        # Exceção: Nomes próprios (Annie)
        if original.strip() in ["Annie", "Ren'Py"]:
            return True
        return False
    
    # Regra 2: Alucinação de Tamanho
    # Se a tradução for 3x maior ou menor que o original, algo está errado.
    len_orig = len(original)
    len_trad = len(traducao)
    if len_orig > 10 and (len_trad > len_orig * 3 or len_trad < len_orig / 3):
        return False
        
    return True

def traduzir_linha(texto_en):
    # Prepara para o MarianMT
    inputs = tokenizer(">>pt<< " + texto_en, return_tensors="pt", padding=True)
    
    # Gera a tradução (Beam Search para qualidade)
    translated_tokens = model.generate(**inputs, max_length=128, num_beams=5)
    traducao = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    
    return traducao

def processar_texto():
    print("\n[3/3] Sistema Pronto. Teste de Mesa (Digite 'sair' para fechar):")
    
    while True:
        original = input("\nFrase Original: ")
        if original.lower() in ['sair', 'exit']: break
        
        # Passo A: Tradução Neural
        traducao = traduzir_linha(original)
        
        # Passo B: Filtro de Sanidade (Lógica)
        passou_sanidade = filtro_sanidade(original, traducao)
        
        if not passou_sanidade:
            confianca = 0.0
            status = "❌ REJEITADO (LÓGICA)"
            obs = "A tradução falhou no teste de sanidade (cópia ou tamanho)."
        else:
            # Passo C: Crítico Neural (Só roda se passar na lógica)
            previsoes, score_bruto = critico.predict([[original, traducao]])
            confianca = float(score_bruto) * 100
            
            if confianca > 70:
                status = "✅ APROVADO"
                obs = "Alta qualidade."
            elif confianca > 45:
                status = "⚠️ ATENÇÃO"
                obs = "Verificar contexto."
            else:
                status = "❌ REJEITADO (CRÍTICO)"
                obs = "O crítico achou a tradução ruim."

        # Relatório
        print(f"-> Tradução: {traducao}")
        print(f"-> Score: {confianca:.2f}% [{status}]")
        print(f"-> Obs: {obs}")

if __name__ == "__main__":
    processar_texto()
