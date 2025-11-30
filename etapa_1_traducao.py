import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# CONFIG
ARQUIVO_ALVO = "script_novo_jogo.rpy"
CAMINHO_MODELO = "./modelo_annie_v1"
ARQUIVO_TEMP = "temp_dados.json"

def extrair_conteudo_manual(linha):
    """
    Corta a string manualmente procurando as aspas.
    Retorna: (indentacao_e_nome, texto_conteudo) ou (None, None)
    """
    linha_limpa = linha.strip()
    if not linha_limpa: return None, None, None
    
    # Encontrar a primeira e a última aspa
    inicio_aspas = linha.find('"')
    fim_aspas = linha.rfind('"')
    
    # Se não tiver duas aspas, ou se elas forem a mesma (só uma aspa no texto)
    if inicio_aspas == -1 or fim_aspas == -1 or inicio_aspas == fim_aspas:
        return None, None, None
        
    # O texto é o miolo
    texto = linha[inicio_aspas+1 : fim_aspas]
    
    # O prefixo (indentação + nome) é tudo antes da primeira aspa
    prefixo_bruto = linha[:inicio_aspas]
    
    # Separar indentação do nome (opcional, mas bom para reconstrução)
    # A indentação são os espaços iniciais
    indentacao = ""
    for char in prefixo_bruto:
        if char.isspace(): indentacao += char
        else: break
        
    nome_char = prefixo_bruto[len(indentacao):] # O resto é o nome
    
    return indentacao, nome_char, texto

def main():
    print("\n--- ETAPA 1: TRADUÇÃO (Annie - V5 Força Bruta) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: Arquivo alvo não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()
        
    tarefas = []
    buffer_original = None
    
    print("Mapeando linhas do arquivo...")
    for i, linha in enumerate(linhas):
        linha = linha.replace("\n", "") # Limpa quebra de linha
        
        # Ignora linhas que não parecem diálogo
        if '"' not in linha: continue

        # CASO 1: É uma linha de ORIGINAL (Começa com #)
        if linha.strip().startswith('#'):
            # Remove o '#' inicial para processar como texto normal
            # Ex: "    # m 'Texto'" vira "      m 'Texto'"
            linha_sem_comentario = linha.replace('#', ' ', 1)
            
            _, _, texto = extrair_conteudo_manual(linha_sem_comentario)
            if texto is not None:
                buffer_original = texto.replace(r'\n', '\n')
            continue

        # CASO 2: É uma linha de TRADUÇÃO
        if buffer_original is not None:
            indent, char, texto = extrair_conteudo_manual(linha)
            
            if texto is not None:
                # Critério: Vazio ou igual ao original (Cópia)
                if texto == "" or texto == buffer_original:
                    tarefas.append({
                        "id": i,
                        "original": buffer_original,
                        "indent": indent,
                        "char": char
                    })
                
            # Resetamos o buffer
            buffer_original = None

    print(f"Novas linhas encontradas para traduzir: {len(tarefas)}")
    
    if not tarefas: 
        print("Aviso: Nenhuma linha encontrada. O arquivo pode já estar todo traduzido.")
        return

    # Traduzir
    print("Carregando modelo...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
        model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)
    except:
        print("Erro ao carregar modelo. Verifique a pasta.")
        return
    
    print("Traduzindo...")
    for i, item in enumerate(tarefas):
        inputs = tokenizer(">>pt<< " + item["original"], return_tensors="pt", padding=True)
        out = model.generate(**inputs, max_length=128, num_beams=2)
        item["pt"] = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"\rProcessado: {i+1}/{len(tarefas)}", end="")
    
    # Salvar
    with open(ARQUIVO_TEMP, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, indent=4)
    
    print("\nEtapa 1 Concluída.")
if __name__ == "__main__":
    main()
