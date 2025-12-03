import os
import json
import re
import time
import google.generativeai as genai
from google.api_core import exceptions

# --- CONFIGURAÇÕES ---
ARQUIVO_JOGO = "script.rpy"
ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_IDENTIDADE = "identidade.json"

# --- COLOQUE SUA CHAVE AQUI (Ou use variável de ambiente) ---
# Você pega grátis em: https://aistudio.google.com/app/apikey
CHAVE_API_GEMINI = "AIzaSyAr7Wv4fh78FHQ8vYSMhFF0TCjVwRlprIk" 

def configurar_ia():
    if CHAVE_API_GEMINI != "COLOQUE_SUA_KEY_AQUI":
        genai.configure(api_key=CHAVE_API_GEMINI)
        return True
    return False

def consultar_oraculo(frase_ingles, contexto_anterior="", contexto_posterior=""):
    """
    O Detetive de Contexto. Tenta 3 vezes antes de desistir.
    """
    if not configurar_ia():
        return "⚠️ API Key não configurada. Edite o script."

    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Analise esta frase de uma Visual Novel em busca de erros de digitação (typos) ou homófonos confusos.
    Contexto: "{contexto_anterior}" ... "{contexto_posterior}"
    Frase Alvo: "{frase_ingles}"
    
    A frase faz sentido? A palavra 'bare' deve ser 'bear'? 'were' deve ser 'where'?
    Se houver erro provável, explique e dê a tradução correta para Português.
    Se estiver tudo certo, apenas diga "Sem erros aparentes".
    Seja breve.
    """

    # Sistema de Retry Automático (Blindagem)
    tentativas = 0
    while tentativas < 3:
        try:
            resposta = modelo.generate_content(prompt)
            return resposta.text
        except Exception as e:
            tentativas += 1
            print(f"\n(IA ocupada, tentando de novo... {tentativas}/3)")
            time.sleep(2) # Espera 2 segundos
            
    return "❌ A IA não respondeu. Tente manualmente."

# --- (O RESTO DAS FUNÇÕES DE CARREGAR/SALVAR CONTINUAM IGUAIS) ---
def carregar_json(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return {} if "identidade" in arquivo else []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_script():
    with open(ARQUIVO_JOGO, "r", encoding="utf-8") as f:
        return f.readlines()

def aprender_identidade(char_id, exemplo_texto):
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    if char_id in identidades: return
    print(f"\n🤔 Personagem novo: '{char_id}'")
    genero = input(f"Gênero? (M/F/N): ").strip().upper()
    if genero in ["M", "F", "N"]:
        identidades[char_id] = {"genero": genero, "obs": "Via Assistente"}
        salvar_json(ARQUIVO_IDENTIDADE, identidades)

def aprender_traducao(original, correcao):
    dataset = carregar_json(ARQUIVO_OURO)
    for item in dataset:
        if item['en'] == original:
            item['pt'] = correcao
            item['score'] = 100.0
            salvar_json(ARQUIVO_OURO, dataset)
            return
    dataset.append({"en": original, "pt": correcao, "score": 100.0, "contexto_vn": "Manual"})
    salvar_json(ARQUIVO_OURO, dataset)

def main():
    print("\n--- ASSISTENTE V3 (Com Oráculo IA) ---")
    tem_ia = configurar_ia()
    
    while True:
        termo = input("\n🔍 Buscar erro (ou 'sair'): ")
        if termo.lower() in ['sair', 'exit']: break
        
        linhas = carregar_script()
        encontrados = []
        
        for i, linha in enumerate(linhas):
            if termo.lower() in linha.lower() and not linha.strip().startswith('#'):
                # Lógica de busca do original
                original = "???"
                char_id = "?"
                for j in range(i-1, max(-1, i-10), -1):
                    l_check = linhas[j].strip()
                    if l_check.startswith('#') and '"' in l_check:
                        original = l_check.replace('#', '').strip()
                        break
                match = re.search(r'^\s*(\w+)\s+', linha)
                if match: char_id = match.group(1)
                
                encontrados.append({"idx": i, "pt": linha.strip(), "en": original, "char": char_id})

        if not encontrados:
            print("Nada encontrado.")
            continue
            
        for n, item in enumerate(encontrados):
            print(f"\n[{n}] {item['pt']}")
        
        sel = input("\nQual linha? (Número): ")
        if not sel.isdigit(): continue
        alvo = encontrados[int(sel)]
        
        # --- MENU DE AÇÃO ---
        print(f"\n--- LINHA {alvo['idx']+1} ---")
        print(f"🇺🇸 {alvo['en']}")
        print(f"🇧🇷 {alvo['pt']}")
        
        acao = input("\n[1] Corrigir Manualmente\n[2] Perguntar à IA (Detetive)\nOpção: ")
        
        if acao == "2":
            if not tem_ia:
                print("⚠️ Configure a CHAVE_API_GEMINI no script primeiro.")
            else:
                print("\n🕵️ Consultando o Oráculo...")
                # Pega contexto simples (linha anterior e posterior se possível)
                ctx_ant = linhas[alvo['idx']-2].strip() if alvo['idx'] > 2 else ""
                ctx_pos = linhas[alvo['idx']+2].strip() if alvo['idx'] < len(linhas)-2 else ""
                
                analise = consultar_oraculo(alvo['en'], ctx_ant, ctx_pos)
                print(f"\n🤖 RELATÓRIO DA IA:\n{analise}")
                
                print("\nAgora que você sabe a verdade, quer corrigir?")
        
        # Fluxo de Correção (Igual ao V2)
        nova_traducao = input("\nDigite a tradução correta (Enter para cancelar): ")
        if nova_traducao:
             # ... (Mesma lógica de salvar do V2) ...
             indent = linhas[alvo['idx']].split('"')[0]
             if '"' not in nova_traducao:
                 linhas[alvo['idx']] = f'{indent}"{nova_traducao}"\n'
             else:
                 linhas[alvo['idx']] = f'{indent}{nova_traducao}\n'
            
             with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f:
                f.writelines(linhas)
             print("✅ Salvo! (SHIFT+R)")
             
             texto_en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
             aprender_traducao(texto_en_limpo, nova_traducao)
             
             if alvo['char'] != "?":
                 aprender_identidade(alvo['char'], nova_traducao)

if __name__ == "__main__":
    main()
