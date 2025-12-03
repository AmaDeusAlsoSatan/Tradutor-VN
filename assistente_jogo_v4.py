import os
import json
import re
import time
import google.generativeai as genai

# --- CONFIGURAÇÕES ---
ARQUIVO_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\Hot_Cocoa_Magic-1.0-pc\game\tl\portuguese\script.rpy" # Caminho do jogo
ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_IDENTIDADE = "identidade.json"

# --- SUA CHAVE AQUI ---
CHAVE_API_GEMINI = "AIzaSyAr7Wv4fh78FHQ8vYSMhFF0TCjVwRlprIk" 

def configurar_ia():
    if "COLOQUE" in CHAVE_API_GEMINI:
        return False
    genai.configure(api_key=CHAVE_API_GEMINI)
    return True

def consultar_ia_autofix(original, atual, contexto_anterior, contexto_posterior):
    """Pede para a IA corrigir o erro e devolver a frase pronta."""
    if not configurar_ia():
        return None, "⚠️ Configure a API Key no script."

    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Você é um especialista em localização de jogos (Inglês -> Português).
    
    SITUAÇÃO:
    O texto original em inglês pode ter erros de digitação (ex: 'bare' em vez de 'bear').
    A tradução atual está estranha ou incorreta.
    
    DADOS:
    Contexto: "{contexto_anterior}" ... "{contexto_posterior}"
    Original (EN): "{original}"
    Atual (PT): "{atual}"
    
    TAREFA:
    1. Identifique se há erro no inglês (typo/homófono).
    2. Gere a tradução CORRETA em Português, adaptada ao contexto e gênero.
    
    RESPOSTA (Siga estritamente este formato):
    EXPLICAÇÃO: [Breve motivo do erro]
    CORRECAO: [Apenas a frase nova em português, sem aspas]
    """

    try:
        resposta = modelo.generate_content(prompt)
        texto = resposta.text
        
        # Extrai a correção e a explicação
        expl = re.search(r'EXPLICAÇÃO:(.*)', texto, re.IGNORECASE)
        corr = re.search(r'CORRECAO:(.*)', texto, re.IGNORECASE)
        
        explicacao = expl.group(1).strip() if expl else "Sem explicação."
        frase_nova = corr.group(1).strip() if corr else ""
        
        # Limpeza extra se a IA colocar aspas
        if frase_nova.startswith('"') and frase_nova.endswith('"'):
            frase_nova = frase_nova[1:-1]
            
        return frase_nova, explicacao

    except Exception as e:
        return None, f"Erro na API: {e}"

# --- FUNÇÕES DE ARQUIVO (IGUAIS) ---
def carregar_json(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f: return json.load(f)
    return {} if "identidade" in arquivo else []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f: json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_script():
    with open(ARQUIVO_JOGO, "r", encoding="utf-8") as f: return f.readlines()

def aprender_traducao(original, correcao):
    # Remove do Silver se existir
    silver = carregar_json("dataset_incubadora_silver.json")
    silver_novo = [x for x in silver if x['en'] != original]
    if len(silver) != len(silver_novo):
        salvar_json("dataset_incubadora_silver.json", silver_novo)
        print("   🥈 Removido da Incubadora.")

    # Adiciona ao Gold
    gold = carregar_json(ARQUIVO_OURO)
    for item in gold:
        if item['en'] == original:
            item['pt'] = correcao
            item['score'] = 100.0
            salvar_json(ARQUIVO_OURO, gold)
            print("   🧠 Memória Gold ATUALIZADA!")
            return

    gold.append({"en": original, "pt": correcao, "score": 100.0, "contexto_vn": "AutoFix_IA"})
    salvar_json(ARQUIVO_OURO, gold)
    print("   🧠 Nova lição aprendida (Gold)!")

def main():
    print("\n--- ASSISTENTE V4 (AUTO-FIX) ---")
    print("Digite parte da frase ERRADA para começar.")
    
    while True:
        termo = input("\n🔍 Buscar erro: ")
        if termo.lower() in ['sair', 'exit']: break
        
        linhas = carregar_script()
        encontrados = []
        
        # Busca inteligente
        for i, linha in enumerate(linhas):
            if termo.lower() in linha.lower() and not linha.strip().startswith('#'):
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
            print("❌ Nada encontrado no script.")
            continue
            
        for n, item in enumerate(encontrados):
            print(f"\n[{n}] PT: {item['pt']}")
            print(f"    EN: {item['en']}")
        
        sel = input("\nQual linha? (Número): ")
        if not sel.isdigit(): continue
        alvo = encontrados[int(sel)]
        
        # --- A MÁGICA ---
        print(f"\n--- LINHA SELECIONADA ---")
        print(f"Original: {alvo['en']}")
        print(f"Atual:    {alvo['pt']}")
        
        acao = input("\n[1] Digitar Correção Manual\n[2] 🤖 PEDIR PARA A IA CONSERTAR\nOpção: ")
        
        nova_traducao = ""
        
        if acao == "2":
            print("\n🤖 IA Analisando contexto e erros de ortografia...")
            ctx_ant = linhas[alvo['idx']-2].strip() if alvo['idx'] > 2 else ""
            ctx_pos = linhas[alvo['idx']+2].strip() if alvo['idx'] < len(linhas)-2 else ""
            
            sugestao, explicacao = consultar_ia_autofix(alvo['en'], alvo['pt'], ctx_ant, ctx_pos)
            
            if sugestao:
                print(f"\n💡 EXPLICACAO: {explicacao}")
                print(f"✨ SUGESTÃO:  \"{sugestao}\"")
                confirmar = input("\nAplicar essa correção? (S/N): ").lower()
                if confirmar == 's':
                    nova_traducao = sugestao
            else:
                print(f"Erro: {explicacao}")

        elif acao == "1":
            nova_traducao = input("Digite a tradução correta: ")

        # APLICAÇÃO
        if nova_traducao:
             indent = linhas[alvo['idx']].split('"')[0]
             prefixo = f"{indent}\""
             if '"' in nova_traducao: # Se a IA mandou com aspas internas, escapamos
                  nova_traducao = nova_traducao.replace('"', r'\"')
             
             # Monta a linha final
             linhas[alvo['idx']] = f'{prefixo}{nova_traducao}"\n'
            
             with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f:
                f.writelines(linhas)
             
             print(f"\n✅ JOGO ATUALIZADO! Linha {alvo['idx']+1} corrigida.")
             print("➡️  Dê SHIFT+R no jogo para ver.")
             
             # Salva no Cérebro
             en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
             aprender_traducao(en_limpo, nova_traducao)

if __name__ == "__main__":
    main()
