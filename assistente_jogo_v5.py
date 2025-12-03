import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- CARREGA SEGREDOS ---
load_dotenv() 
API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURAÇÕES ---
# SEU CAMINHO (Mantido)
ARQUIVO_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\Hot_Cocoa_Magic-1.0-pc\game\tl\portuguese\script.rpy"

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"
ARQUIVO_IDENTIDADE = "identidade.json"

def configurar_ia():
    if not API_KEY: return False
    genai.configure(api_key=API_KEY)
    return True

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, "r", encoding="utf-8") as f: return json.load(f)
    return {} if "identidade" in arquivo else []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f: json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_script():
    with open(ARQUIVO_JOGO, "r", encoding="utf-8") as f: return f.readlines()

def aprender_traducao(original, correcao):
    print(f"\n🔄 Salvando no Cérebro: '{original[:20]}...'")
    gold = carregar_json(ARQUIVO_OURO)
    silver = carregar_json(ARQUIVO_PRATA)
    
    # Remove do Silver
    silver = [item for item in silver if item['en'] != original]
    salvar_json(ARQUIVO_PRATA, silver)

    # Adiciona ao Gold
    encontrado = False
    for item in gold:
        if item['en'] == original:
            item['pt'] = correcao
            item['score'] = 100.0
            item['contexto_vn'] = "Correcao_Manual_Assistente"
            encontrado = True
            break
    
    if not encontrado:
        gold.append({"en": original, "pt": correcao, "score": 100.0, "contexto_vn": "Correcao_Manual"})
    
    salvar_json(ARQUIVO_OURO, gold)
    print("✅ Memória Atualizada!")

def aprender_identidade(char_id, exemplo_texto):
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    if char_id in identidades: return
    print(f"\n🤔 Personagem novo: '{char_id}'")
    genero = input(f"Gênero? (M/F/N - Enter para ignorar): ").strip().upper()
    if genero in ["M", "F", "N"]:
        identidades[char_id] = {"genero": genero, "obs": "Via Assistente"}
        salvar_json(ARQUIVO_IDENTIDADE, identidades)

def consultar_ia_autofix(original, atual, ant, pos):
    if not configurar_ia(): return None, "Sem API Key."
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Especialista em tradução.
    Contexto: "{ant}" ... "{pos}"
    Original: "{original}"
    Atual: "{atual}"
    Tarefa: Identifique erros (typos como bare/bear) e corrija para PT-BR.
    Formato: 
    EXPLICAÇÃO: [motivo]
    CORRECAO: [frase]
    """
    try:
        res = modelo.generate_content(prompt).text
        expl = re.search(r'EXPLICAÇÃO:(.*)', res, re.IGNORECASE)
        corr = re.search(r'CORRECAO:(.*)', res, re.IGNORECASE)
        frase = corr.group(1).strip() if corr else ""
        if frase.startswith('"') and frase.endswith('"'): frase = frase[1:-1]
        return frase, expl.group(1).strip() if expl else ""
    except Exception as e: return None, str(e)

def autocompletar_ia(parcial, original_completo):
    """A Mágica dos Três Pontinhos (...)"""
    if not configurar_ia(): return parcial # Fallback se não tiver IA
    
    print("✨ IA analisando como fundir sua correção...")
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    TAREFA: Merge de Texto Inteligente.
    
    FRASE ORIGINAL: "{original_completo}"
    CORREÇÃO DO USUÁRIO: "{parcial}"
    
    O usuário digitou o início da frase e usou "..." para indicar que quer manter o restante da frase original, mas adaptando a gramática (gênero/número) se necessário para combinar com a correção.
    
    Retorne APENAS a frase completa resultante. Nada mais.
    """
    try:
        res = modelo.generate_content(prompt).text.strip()
        # Remove aspas se a IA colocar
        if res.startswith('"') and res.endswith('"'): res = res[1:-1]
        return res
    except:
        return parcial

def main():
    print("\n--- ASSISTENTE DE JOGO V5.1 (Smart Autocomplete) ---")
    print("Dica: Use '...' no final para a IA completar a frase.")
    
    while True:
        termo = input("\n🔍 Buscar erro (ou 'sair'): ")
        if termo.lower() in ['sair', 'exit']: break
        
        linhas = carregar_script()
        encontrados = []
        
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
            print("❌ Nada encontrado.")
            continue
            
        for n, item in enumerate(encontrados):
            print(f"\n[{n}] PT: {item['pt']}")
            print(f"    EN: {item['en']}")
        
        while True:
            sel = input("\nQual linha? (Número) [Enter p/ cancelar]: ")
            if not sel: 
                alvo = None
                break
            if sel.isdigit() and 0 <= int(sel) < len(encontrados):
                alvo = encontrados[int(sel)]
                break
            print("❌ Número inválido.")
        
        if not alvo: continue

        print(f"\n--- EDITANDO LINHA {alvo['idx']+1} ---")
        print("[1] Correção Manual (Use '...' p/ completar)")
        print("[2] Auto-Fix (IA Total)")
        opcao = input("Opção: ")
        
        nova_traducao = ""
        
        if opcao == "2":
            # ... (Mesma lógica Auto-Fix) ...
            ctx_ant = linhas[alvo['idx']-2].strip() if alvo['idx'] > 2 else ""
            ctx_pos = linhas[alvo['idx']+2].strip() if alvo['idx'] < len(linhas)-2 else ""
            sugestao, motivo = consultar_ia_autofix(alvo['en'], alvo['pt'], ctx_ant, ctx_pos)
            if sugestao:
                print(f"\n💡 MOTIVO: {motivo}")
                print(f"✨ SUGESTÃO: \"{sugestao}\"")
                if input("Aplicar? (s/n): ").lower() == 's': nova_traducao = sugestao

        elif opcao == "1":
            entrada = input("Digite a correção: ")
            
            # --- LÓGICA INTELIGENTE DOS 3 PONTINHOS ---
            if entrada.strip().endswith("..."):
                texto_original_limpo = alvo['pt'].split('"')[1] if '"' in alvo['pt'] else alvo['pt']
                nova_traducao = autocompletar_ia(entrada, texto_original_limpo)
                
                print(f"\n✨ IA Completou: \"{nova_traducao}\"")
                if input("Confirmar? (s/n): ").lower() != 's':
                    nova_traducao = "" # Cancelou
            else:
                nova_traducao = entrada

        if nova_traducao:
            indent = linhas[alvo['idx']].split('"')[0]
            if '"' in nova_traducao: nova_traducao = nova_traducao.replace('"', r'\"')
            
            linhas[alvo['idx']] = f'{indent}"{nova_traducao}"\n'
            
            with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f:
                f.writelines(linhas)
            
            print(f"\n✅ Jogo Atualizado! Dê SHIFT+R.")
            
            # Aprender
            en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
            aprender_traducao(en_limpo, nova_traducao)
            
            if alvo['char'] != "?":
                aprender_identidade(alvo['char'], nova_traducao)

if __name__ == "__main__":
    main()
