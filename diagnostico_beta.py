import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel
from difflib import SequenceMatcher

# --- CONFIGURAÇÕES ---
# O seu modelo treinado (Annie)
CAMINHO_SEU_MODELO = "./modelo_annie_v1"
# O modelo oficial reverso (Para fazer a prova real: PT -> EN)
MODELO_REVERSO = "Helsinki-NLP/opus-mt-ROMANCE-en"

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

print("--- CARREGANDO O TRIBUNAL DA IA (Isso pode demorar na 1ª vez pois vai baixar o Reverso) ---")

# 1. Carregar Tradutor (Ida)
print("[1/3] Carregando seu Tradutor (EN -> PT)...")
try:
    tokenizer_ida = AutoTokenizer.from_pretrained(CAMINHO_SEU_MODELO)
    model_ida = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_SEU_MODELO)
except:
    print("Erro: Não achei a pasta './modelo_annie_v1'. Você rodou o treinamento?")
    exit()

# 2. Carregar Auditor (Volta)
print("[2/3] Baixando/Carregando Auditor Reverso (PT -> EN)...")
try:
    tokenizer_volta = AutoTokenizer.from_pretrained(MODELO_REVERSO)
    model_volta = AutoModelForSeq2SeqLM.from_pretrained(MODELO_REVERSO)
except Exception as e:
    print(f"Erro ao baixar modelo reverso: {e}")
    exit()

# 3. Carregar Juiz (QE)
print("[3/3] Acordando o Juiz (TransQuest)...")
critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)

def testar_frase(frase_en):
    print(f"\n{'='*40}")
    print(f"ANÁLISE FORENSE: '{frase_en}'")
    print(f"{'='*40}")
    
    # PASSO 1: IDA (Seu modelo traduz)
    inputs = tokenizer_ida(">>pt<< " + frase_en, return_tensors="pt", padding=True)
    out = model_ida.generate(**inputs, max_length=128)
    traducao_pt = tokenizer_ida.decode(out[0], skip_special_tokens=True)
    print(f"1. TRADUÇÃO (Ida):      '{traducao_pt}'")

    # PASSO 2: VOLTA (Modelo Reverso traduz de volta para inglês)
    inputs_back = tokenizer_volta(">>en<< " + traducao_pt, return_tensors="pt", padding=True)
    out_back = model_volta.generate(**inputs_back, max_length=128)
    back_en = tokenizer_volta.decode(out_back[0], skip_special_tokens=True)
    print(f"2. AUDITORIA (Volta):   '{back_en}'")

    # CÁLCULOS MATEMÁTICOS
    # Compara o Inglês Original com o Inglês da Volta
    nota_back = similaridade(frase_en.lower(), back_en.lower()) * 100
    
    # O Crítico avalia a qualidade PT-EN
    _, score_qe = critico.predict([[frase_en, traducao_pt]])
    nota_qe = float(score_qe) * 100
    
    # A FÓRMULA DO BETA TESTER
    # Damos peso para Fluência (60%) e para Fidelidade (40%)
    nota_final = (nota_qe * 0.6) + (nota_back * 0.4)

    print(f"\n--- O VEREDITO ---")
    print(f"Nota de Fidelidade (Back-Translation): {nota_back:.1f}%")
    print(f"Nota de Fluência (TransQuest):         {nota_qe:.1f}%")
    print(f"---------------------------------------")
    print(f"NOTA FINAL PONDERADA:                  {nota_final:.1f}%")

    if nota_final > 90:
        print("\n🌟 RESULTADO: APROVADO COM LOUVOR")
        print("   (Essa frase seria salva no 'dataset_auto_treino.json' para o robô aprender)")
    elif nota_final > 75:
        print("\n✅ RESULTADO: APROVADO")
        print("   (Tradução segura, vai para o jogo)")
    else:
        print("\n❌ RESULTADO: REJEITADO")
        print("   (O sistema tentaria outra variação da frase automaticamente)")

while True:
    txt = input("\nDigite uma frase em Inglês para testar (ou 'sair'): ")
    if txt.lower() in ["sair", "exit"]: break
    testar_frase(txt)
