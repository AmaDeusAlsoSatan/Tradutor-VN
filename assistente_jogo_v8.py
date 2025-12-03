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
ARQUIVO_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\Hot_Cocoa_Magic-1.0-pc\game\tl\portuguese\script.rpy"

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"
ARQUIVO_IDENTIDADE = "identidade.json"

# --- SELEÇÃO DE MODELO ---
MODELO_PREFERIDO = 'models/gemini-2.0-flash' 
MODELO_FALLBACK = 'models/gemini-pro-latest'

def configurar_ia():
    if not API_KEY: return False
    genai.configure(api_key=API_KEY)
    return True

def obter_modelo_seguro():
    try: return genai.GenerativeModel(MODELO_PREFERIDO)
    except: return genai.GenerativeModel(MODELO_FALLBACK)

def limpar_markdown(texto):
    if not texto: return ""
    texto = texto.replace("**", "").replace("*", "")
    texto = texto.strip()
    # Remove aspas do início/fim se a IA colocou
    if texto.startswith('"') and texto.endswith('"'):
        texto = texto[1:-1]
    # Remove nome do personagem se a IA colocou (ex: m "texto")
    match = re.match(r'^\w+\s+"(.*)"$', texto)
    if match:
        texto = match.group(1)
    return texto.strip()

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
    
    silver = [item for item in silver if item['en'] != original]
    salvar_json(ARQUIVO_PRATA, silver)

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

# --- A CORREÇÃO ESTÁ AQUI ---
def consultar_ia_autofix(original, atual, ant, pos, char_id, identidades):
    if not configurar_ia(): return None, "Sem API Key."
    print("   ...Consultando a IA (Com Identidade)...")
    
    # Monta a ficha do personagem para a IA
    info_char = ""
    if char_id in identidades:
        dados = identidades[char_id]
        info_char = f"\n    INFORMAÇÃO CRÍTICA: O personagem '{char_id}' é do gênero {dados['genero']}. Use concordância correta (ex: obrigada, cansada)."

    try:
        modelo = obter_modelo_seguro()
        
        prompt = f"""
        Atue como um Editor Sênior de Localização de Jogos (EN -> PT-BR).
        
        CONTEXTO: "{ant}" ... "{pos}"
        {info_char}
        
        ORIGINAL: "{original}"
        ATUAL: "{atual}"
        
        TAREFA:
        1. Corrija a tradução para Português natural.
        2. Respeite o GÊNERO do personagem informado acima.
        3. Corrija erros de fonte (typos em inglês).
        
        SAÍDA OBRIGATÓRIA:
        EXPLICAÇÃO: [motivo breve]
        CORRECAO: [apenas o texto do diálogo, sem o nome do personagem]
        """
        
        try:
            res = modelo.generate_content(prompt).text
        except:
            # Fallback
            modelo_bkp = genai.GenerativeModel(MODELO_FALLBACK)
            res = modelo_bkp.generate_content(prompt).text

        expl = re.search(r'\*?EXPLICAÇÃO:?\*?\s*(.*)', res, re.IGNORECASE)
        corr = re.search(r'\*?CORRECAO:?\*?\s*(.*)', res, re.IGNORECASE)
        
        frase = limpar_markdown(corr.group(1)) if corr else ""
        motivo = limpar_markdown(expl.group(1)) if expl else "IA não explicou."
        
        if not frase and "\n" in res:
             frase = limpar_markdown(res.strip().split('\n')[-1])

        return frase, motivo
    except Exception as e: return None, str(e)

def autocompletar_ia(parcial, original_completo):
    if not configurar_ia(): return parcial
    print("✨ IA completando...")
    try:
        modelo = obter_modelo_seguro()
        prompt = f"""
        Complete a tradução em PT-BR.
        Original EN: "{original_completo}"
        Início PT: "{parcial}"
        Retorne APENAS a frase completa.
        """
        res = modelo.generate_content(prompt).text
        return limpar_markdown(res)
    except: return parcial

def main():
    print("\n--- ASSISTENTE DE JOGO V8 (Com Memória de Gênero) ---")
    
    # Carrega identidades no início
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    
    while True:
        termo = input("\n🔍 Buscar erro (ou 'sair'): ").strip()
        if termo.lower() in ['sair', 'exit']: break
        if not termo: continue
        
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
            # Mostra se a IA já sabe o gênero
            info_extra = ""
            if item['char'] in identidades:
                info_extra = f" [{identidades[item['char']]['genero']}]"
            
            print(f"\n[{n}] PT: {item['pt']}")
            print(f"    EN: {item['en']} (Char: {item['char']}{info_extra})")
        
        while True:
            sel = input("\nQual linha? (Número) [Enter p/ cancelar]: ").strip()
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
        opcao = input("Opção: ").strip()
        
        nova_traducao = ""
        
        if opcao == "2":
            ctx_ant = linhas[alvo['idx']-2].strip() if alvo['idx'] > 2 else ""
            ctx_pos = linhas[alvo['idx']+2].strip() if alvo['idx'] < len(linhas)-2 else ""
            
            # Passamos a identidade e o ID do char
            sugestao, motivo = consultar_ia_autofix(alvo['en'], alvo['pt'], ctx_ant, ctx_pos, alvo['char'], identidades)
            
            if sugestao:
                print(f"\n💡 MOTIVO: {motivo}")
                print(f"✨ SUGESTÃO: \"{sugestao}\"")
                if input("Aplicar? (s/n): ").strip().lower() == 's': nova_traducao = sugestao
            else:
                print(f"\n❌ Erro: {motivo}")

        elif opcao == "1":
            entrada = input("Digite a correção: ")
            if entrada.strip().endswith("..."):
                en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
                nova_traducao = autocompletar_ia(entrada, en_limpo)
                print(f"\n✨ IA Completou: \"{nova_traducao}\"")
                if input("Confirmar? (s/n): ").strip().lower() != 's': nova_traducao = ""
            else:
                nova_traducao = entrada
        else:
            print("❌ Opção inválida.")

        if nova_traducao:
            indent = linhas[alvo['idx']].split('"')[0]
            if '"' in nova_traducao: nova_traducao = nova_traducao.replace('"', r'\"')
            
            linhas[alvo['idx']] = f'{indent}"{nova_traducao}"\n'
            
            with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f:
                f.writelines(linhas)
            
            print(f"\n✅ Jogo Atualizado! Dê SHIFT+R.")
            
            en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
            aprender_traducao(en_limpo, nova_traducao)
            
            if alvo['char'] != "?":
                aprender_identidade(alvo['char'], nova_traducao)
                # Recarrega identidades para a próxima consulta
                identidades = carregar_json(ARQUIVO_IDENTIDADE)

if __name__ == "__main__":
    main()
