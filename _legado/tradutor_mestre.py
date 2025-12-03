import os
import re
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transquest.algo.sentence_level.monotransquest.run_model import MonoTransQuestModel

# --- CONFIGURAÇÕES ---
CAMINHO_MODELO = "./modelo_annie_v1"  # Seu cérebro treinado
ARQUIVO_ALVO = "script_novo_jogo.rpy" # Mude isso para o arquivo do próximo jogo

print("--- INICIANDO A FÁBRICA DE TRADUÇÃO MESTRE ---")

# 1. Carregar Modelos (Só uma vez)
print("[1/3] Carregando a IA Treinada...")
tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)

print("[2/3] Carregando o Crítico de Qualidade...")
critico = MonoTransQuestModel("xlmroberta", "TransQuest/monotransquest-da-multilingual", use_cuda=False)

def traduzir_linha(texto_en):
    inputs = tokenizer(">>pt<< " + texto_en, return_tensors="pt", padding=True)
    # num_beams=5 garante que ele pense em 5 opções e escolha a melhor
    translated_tokens = model.generate(**inputs, max_length=128, num_beams=5)
    return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)

def avaliar_qualidade(original, traducao):
    # 1. Filtro de Sanidade (Lógica)
    if original.strip() == traducao.strip() and len(original) > 4:
        if original.strip() not in ["Annie", "Ren'Py"]: # Exceções
            return 0.0, "CÓPIA_DETECTADA"
            
    # 2. Crítico Neural
    _, score = critico.predict([[original, traducao]])
    return float(score) * 100, "NEURAL"

def processar_arquivo():
    if not os.path.exists(ARQUIVO_ALVO):
        print(f"Erro: Coloque o arquivo '{ARQUIVO_ALVO}' nesta pasta para traduzir.")
        return

    print(f"[3/3] Traduzindo '{ARQUIVO_ALVO}'...")
    
    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    # Regex para capturar texto do RenPy
    regex_traducao = re.compile(r'^(\s*)(?:(\w+)\s+)?\"(.*)\"')
    regex_original = re.compile(r'^\s*#\s*(?:(\w+)\s+)?\"(.*)\"')

    buffer_original = None
    contador = 0

    for i, linha in enumerate(linhas):
        # Captura o original comentado
        match_orig = regex_original.match(linha)
        if match_orig:
            buffer_original = match_orig.group(2).replace(r'\n', '\n')
        
        # Captura a linha de tradução (vazia ou não)
        match_trad = regex_traducao.match(linha)
        
        if match_trad and buffer_original:
            indentacao = match_trad.group(1)
            char_nome = match_trad.group(2) or ""
            conteudo_atual = match_trad.group(3)

            # Se estiver vazio, traduz
            if conteudo_atual.strip() == "" or conteudo_atual == buffer_original:
                print(f"Traduzindo: {buffer_original[:30]}...")
                
                traducao = traduzir_linha(buffer_original)
                score, tipo = avaliar_qualidade(buffer_original, traducao)
                
                # Se a qualidade for ruim, adiciona um aviso no arquivo para você ver depois
                aviso = ""
                if score < 50:
                    aviso = f" # [ATENÇÃO: Qualidade Baixa ({score:.1f}%)]"
                    print(f"   >>> ALERTA: Qualidade baixa detectada ({score:.1f}%)")

                # Formatação final
                traducao_safe = traducao.replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{char_nome} " if char_nome else ""
                nova_linha = f'{indentacao}{prefixo}"{traducao_safe}"{aviso}\n'
                
                novas_linhas.append(nova_linha)
                contador += 1
            else:
                novas_linhas.append(linha) # Já estava feito
            
            buffer_original = None # Limpa
        else:
            novas_linhas.append(linha)

    # Salva o arquivo traduzido
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"\n--- SUCESSO! ---")
    print(f"Linhas traduzidas: {contador}")
    print(f"Arquivo salvo: {ARQUIVO_ALVO}")

if __name__ == "__main__":
    processar_arquivo()
