import os
import re
import json
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# CONFIG
ARQUIVO_ALVO = "script_novo_jogo.rpy"
CAMINHO_MODELO = "./modelo_annie_v1"
ARQUIVO_TEMP = "temp_dados.json"

def main():
    print("\n--- ETAPA 1: TRADUÇÃO (Annie - V2 Regex Fix) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: Arquivo alvo não encontrado.")
        return

    # Mapear linhas
    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        
    tarefas = []
    # CORREÇÃO DE REGEX: Agora aceita nomes compostos (ex: 'w s m')
    regex_traducao = re.compile(r'^(\s*)(?:(.+?)\s+)?\"(.*)\"')
    regex_original = re.compile(r'^\s*#\s*(?:(.+?)\s+)?\"(.*)\"')
    buffer = None
    
    print("Mapeando linhas do arquivo...")
    for i, linha in enumerate(linhas):
        match_orig = regex_original.match(linha)
        if match_orig:
            # Captura o texto original comentado
            buffer = match_orig.group(2).replace(r'\n', '\n')
        
        match_trad = regex_traducao.match(linha)
        if match_trad and buffer:
            conteudo = match_trad.group(3)
            # Se a linha estiver vazia ("") ou igual ao original (cópia), marca para traduzir
            if conteudo.strip() == "" or conteudo == buffer:
                tarefas.append({
                    "id": i,
                    "original": buffer,
                    "indent": match_trad.group(1),
                    # group(2) é o nome/atributos. Se for None, vira string vazia
                    "char": match_trad.group(2) if match_trad.group(2) else ""
                })
            buffer = None

    print(f"Novas linhas encontradas para traduzir: {len(tarefas)}")
    
    if not tarefas: 
        print("Tudo parece já estar traduzido! Verifique o arquivo.")
        return

    # Traduzir
    print("Carregando modelo...")
    tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
    model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)
    
    print("Traduzindo...")
    for i, item in enumerate(tarefas):
        inputs = tokenizer(">>pt<< " + item["original"], return_tensors="pt", padding=True)
        out = model.generate(**inputs, max_length=128, num_beams=2)
        item["pt"] = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"\rProcessado: {i+1}/{len(tarefas)}", end="")
    
    # Salvar estado para a próxima etapa
    with open(ARQUIVO_TEMP, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, indent=4)
    
    print("\nEtapa 1 Concluída. Arquivo temporário salvo.")

if __name__ == "__main__":
    main()
