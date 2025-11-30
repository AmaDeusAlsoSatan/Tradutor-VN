import os
import re
import chromadb # O Cérebro Eterno
from chromadb.utils import embedding_functions
import requests
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script.rpy" # O arquivo do jogo atual
URL_LM_STUDIO = "http://127.0.0.1:1234/v1/chat/completions"
MODELO_IA = "qwen-2.5-1.5b-instruct"

# --- O CÉREBRO ETERNO (MEMÓRIA) ---
# Cria/Carrega o banco de dados na pasta 'memoria_eterna'
chroma_client = chromadb.PersistentClient(path="./memoria_eterna")
# Usa um modelo leve para entender significados
embedding_func = embedding_functions.DefaultEmbeddingFunction()
memoria_colecao = chroma_client.get_or_create_collection(
    name="conhecimento_vn", 
    embedding_function=embedding_func
)

# --- PROMPT DO BETA TESTER (O JOGADOR) ---
PROMPT_BETA_TESTER = """
SISTEMA: Você é um Beta Tester e Editor de Localização de Jogos Sênior.
Seu trabalho é garantir que a tradução faça sentido dentro da HISTÓRIA.

CONTEXTO NARRATIVO (O que aconteceu antes):
{contexto}

ANÁLISE DE CONTEXTO (O que você deve verificar):
1. AMBIGUIDADE: "It's cool" é "Legal" ou "Frio"? (Olhe o contexto: clima ou gíria?)
2. REGÊNCIA: "Diving for" é "Mergulhando para" (Errado) ou "Em busca de" (Certo)?
3. CONSISTÊNCIA: Nomes e termos técnicos estão mantidos?

INSTRUÇÃO:
Analise a TRADUÇÃO SUGERIDA para o ORIGINAL.
Se estiver perfeita e contextualizada, retorne apenas: [APROVADO]
Se houver perda de sentido ou erro de contexto, REESCREVA a tradução final.
Não explique. Apenas a frase corrigida.
"""

def consultar_memoria(texto_original):
    """Busca no banco de dados se já aprendemos algo parecido"""
    resultados = memoria_colecao.query(
        query_texts=[texto_original],
        n_results=1
    )
    
    if resultados['documents'] and resultados['documents'][0]:
        # Se a distância for pequena, significa que é muito parecido
        if resultados['distances'][0][0] < 0.2: 
            return resultados['documents'][0][0]
    return None

def aprender_novo_conceito(original, traducao_final):
    """Salva o acerto na memória eterna"""
    # Só salva se não for trivial
    memoria_colecao.upsert(
        documents=[traducao_final],
        metadatas=[{"original": original}],
        ids=[str(hash(original))] # ID único baseado no texto
    )

def chamar_ia(mensagens):
    try:
        response = requests.post(URL_LM_STUDIO, json={
            "model": MODELO_IA,
            "messages": mensagens,
            "temperature": 0.1,
            "max_tokens": 300
        }, timeout=40)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except:
        pass
    return None

def pipeline_autonomo(texto_original, historico_contexto):
    # 1. CONSULTA A MEMÓRIA ETERNA (O Robô já viu isso antes?)
    memoria = consultar_memoria(texto_original)
    if memoria:
        print(f"   [MEMÓRIA] Lembrei disso: '{memoria}'")
        return memoria

    # 2. TRADUÇÃO INICIAL (O Rascunho)
    prompt_tradutor = [
        {"role": "system", "content": "Traduza para PT-BR. Mantenha o sentido."},
        {"role": "user", "content": texto_original}
    ]
    rascunho = chamar_ia(prompt_tradutor)
    if not rascunho: return texto_original # Falha segura

    # 3. O BETA TESTER JOGA (Validação com Contexto)
    # Prepara o contexto (últimas 3 frases)
    contexto_str = "\n".join(historico_contexto[-3:]) 
    prompt_final = PROMPT_BETA_TESTER.format(contexto=contexto_str)
    
    msg_beta = [
        {"role": "system", "content": prompt_final},
        {"role": "user", "content": f"Original: {texto_original}\nRascunho: {rascunho}"}
    ]
    
    veredito = chamar_ia(msg_beta)
    
    if veredito and "[APROVADO]" not in veredito:
        # O Beta Tester corrigiu!
        traducao_final = veredito.replace("[CORRIGIDO]", "").strip()
        print(f"   [BETA TESTER] Corrigiu contexto: '{rascunho}' -> '{traducao_final}'")
    else:
        # O Beta Tester aprovou
        traducao_final = rascunho

    # 4. APRENDIZADO (Salva no Cérebro Eterno)
    aprender_novo_conceito(texto_original, traducao_final)
    
    return traducao_final

def processar_jogo():
    print("--- INICIANDO BETA TESTER AUTÔNOMO (V10) ---")
    print("Conectando à Memória Eterna...")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Arquivo não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    regex_dialogo = re.compile(r'^\s*#\s*(?:(\w+)\s+)?\"(.*)\"', re.DOTALL)
    regex_traducao = re.compile(r'^(\s*)(?:(\w+)\s+)?\"(.*)\"', re.DOTALL)

    buffer_original = None
    historico_contexto = ["Início da história."] # Memória de curto prazo para o Beta Tester

    for i, linha in enumerate(linhas):
        match_orig = regex_dialogo.match(linha)
        if match_orig:
            buffer_original = match_orig.group(2).replace('\\n', '\n')
        
        match_trad = regex_traducao.match(linha)
        
        if match_trad and buffer_original:
            indentacao = match_trad.group(1)
            char_nome = match_trad.group(2) or ""
            conteudo_atual = match_trad.group(3)
            
            # Normaliza
            conteudo_limpo = conteudo_atual.replace('\\n', '\n')
            
            # Se precisar traduzir (vazio ou igual ao inglês)
            if conteudo_limpo.strip() == "" or conteudo_limpo == buffer_original:
                print(f"[LENDO] {buffer_original[:40]}...")
                
                # CHAMA O PIPELINE AUTÔNOMO
                nova_traducao = pipeline_autonomo(buffer_original, historico_contexto)
                
                # Atualiza o contexto para a próxima frase
                historico_contexto.append(f"Original: {buffer_original} | Tradução: {nova_traducao}")
                
                # Formata para salvar
                nova_traducao_safe = nova_traducao.replace('\n', '\\n').replace('"', '\\"')
                prefixo = f"{char_nome} " if char_nome else ""
                novas_linhas.append(f'{indentacao}{prefixo}"{nova_traducao_safe}"\n')
                
                buffer_original = None
            else:
                # Já estava traduzido, mas adicionamos ao contexto para o Beta Tester saber onde estamos
                historico_contexto.append(f"Contexto: {conteudo_limpo}")
                novas_linhas.append(linha)
                buffer_original = None
        else:
            novas_linhas.append(linha)

    # Salva o arquivo final
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)
    
    print("\n--- Jogo Processado e Conhecimento Armazenado ---")

if __name__ == "__main__":
    processar_jogo()
