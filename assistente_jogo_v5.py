import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- CARREGA SEGREDOS ---
load_dotenv() # Lê o arquivo .env
API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURAÇÕES ---
# CAMINHO ABSOLUTO DO JOGO (MANTENHA O SEU CAMINHO AQUI)
ARQUIVO_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\Hot_Cocoa_Magic-1.0-pc\game\tl\portuguese\script.rpy"

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"
ARQUIVO_IDENTIDADE = "identidade.json"

def configurar_ia():
    if not API_KEY:
        return False
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

# --- A LÓGICA TURBINADA (V3) DE APRENDIZADO ---
def aprender_traducao(original, correcao):
    print(f"\n🔄 Processando aprendizado para: '{original[:30]}...'")
    
    # 1. Carregar os Datasets
    gold = carregar_json(ARQUIVO_OURO)
    silver = carregar_json(ARQUIVO_PRATA)
    
    # 2. Remover do Silver (Promoção)
    # Se a frase estava na incubadora, agora ela graduou!
    silver_inicial = len(silver)
    silver = [item for item in silver if item['en'] != original]
    
    if len(silver) < silver_inicial:
        print("   🥈 Removido da Incubadora (Silver) -> Promovido!")
        salvar_json(ARQUIVO_PRATA, silver)

    # 3. Adicionar/Atualizar no Gold
    encontrado_gold = False
    for item in gold:
        if item['en'] == original:
            print(f"   ⚠️ Atualizando entrada existente no Gold.")
            print(f"      Antigo: {item['pt']}")
            print(f"      Novo:   {correcao}")
            item['pt'] = correcao
            item['score'] = 100.0 # Nota máxima (Humano/Admin)
            item['contexto_vn'] = "Correcao_Manual_Assistente"
            encontrado_gold = True
            break
    
    if not encontrado_gold:
        print("   ✨ Criando nova entrada Ouro.")
        gold.append({
            "en": original,
            "pt": correcao,
            "score": 100.0,
            "contexto_vn": "Correcao_Manual_Assistente"
        })
    
    salvar_json(ARQUIVO_OURO, gold)
    print("✅ Cérebro da IA atualizado com sucesso!")

def aprender_identidade(char_id, exemplo_texto):
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    if char_id in identidades: return
    print(f"\n🤔 Personagem novo detectado: '{char_id}'")
    genero = input(f"Qual o gênero? (M/F/N - Enter para ignorar): ").strip().upper()
    if genero in ["M", "F", "N"]:
        identidades[char_id] = {"genero": genero, "obs": "Via Assistente"}
        salvar_json(ARQUIVO_IDENTIDADE, identidades)

def consultar_ia_autofix(original, atual, contexto_anterior, contexto_posterior):
    if not configurar_ia():
        return None, "⚠️ Crie o arquivo .env com a GEMINI_API_KEY."

    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Você é um especialista em localização de jogos (Inglês -> Português).
    
    CONTEXTO:
    Anterior: "{contexto_anterior}"
    Posterior: "{contexto_posterior}"
    
    PROBLEMA:
    Original (EN): "{original}"
    Tradução Atual (PT): "{atual}"
    
    TAREFA:
    Identifique erros de digitação no inglês (ex: 'bare' vs 'bear') ou erros de tradução.
    Forneça a tradução CORRETA em Português do Brasil.
    
    RESPOSTA (Formato Estrito):
    EXPLICAÇÃO: [Motivo breve]
    CORRECAO: [Frase corrigida sem aspas]
    """

    try:
        resposta = modelo.generate_content(prompt)
        texto = resposta.text
        
        expl = re.search(r'EXPLICAÇÃO:(.*)', texto, re.IGNORECASE)
        corr = re.search(r'CORRECAO:(.*)', texto, re.IGNORECASE)
        
        explicacao = expl.group(1).strip() if expl else "Sem explicação."
        frase_nova = corr.group(1).strip() if corr else ""
        
        if frase_nova.startswith('"') and frase_nova.endswith('"'):
            frase_nova = frase_nova[1:-1]
            
        return frase_nova, explicacao

    except Exception as e:
        return None, f"Erro na API: {e}"

def main():
    print("\n--- ASSISTENTE DE JOGO V5 (Seguro + Inteligente) ---")
    print("Digite parte da frase para corrigir.")
    
    if not API_KEY:
        print("⚠️ AVISO: Arquivo .env não encontrado ou sem chave. O modo Auto-Fix não funcionará.")
    
    while True:
        termo = input("\n🔍 Buscar erro (ou 'sair'): ")
        if termo.lower() in ['sair', 'exit']: break
        
        linhas = carregar_script()
        encontrados = []
        
        for i, linha in enumerate(linhas):
            if termo.lower() in linha.lower() and not linha.strip().startswith('#'):
                original = "???"
                char_id = "?"
                # Busca original no comentário acima
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
        
        sel = input("\nQual linha? (Número): ")
        if not sel.isdigit(): continue
        alvo = encontrados[int(sel)]
        
        # Ações
        print(f"\n--- EDITANDO LINHA {alvo['idx']+1} ---")
        print("[1] Correção Manual")
        print("[2] Auto-Fix (IA)")
        opcao = input("Opção: ")
        
        nova_traducao = ""
        
        if opcao == "2":
            print("🤖 Consultando IA...")
            ctx_ant = linhas[alvo['idx']-2].strip() if alvo['idx'] > 2 else ""
            ctx_pos = linhas[alvo['idx']+2].strip() if alvo['idx'] < len(linhas)-2 else ""
            
            sugestao, motivo = consultar_ia_autofix(alvo['en'], alvo['pt'], ctx_ant, ctx_pos)
            if sugestao:
                print(f"\n💡 MOTIVO: {motivo}")
                print(f"✨ SUGESTÃO: \"{sugestao}\"")
                if input("Aplicar? (s/n): ").lower() == 's':
                    nova_traducao = sugestao
            else:
                print(f"Erro na IA: {motivo}")
        
        elif opcao == "1":
            nova_traducao = input("Digite a correção: ")
            
        # Salvar e Aprender
        if nova_traducao:
            indent = linhas[alvo['idx']].split('"')[0]
            # Tratamento de aspas
            if '"' in nova_traducao:
                 nova_traducao = nova_traducao.replace('"', r'\"')
            
            linhas[alvo['idx']] = f'{indent}"{nova_traducao}"\n'
            
            with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f:
                f.writelines(linhas)
            
            print(f"\n✅ Jogo Atualizado! Dê SHIFT+R.")
            
            # Lógica de Promoção V3
            en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
            aprender_traducao(en_limpo, nova_traducao)
            
            if alvo['char'] != "?":
                aprender_identidade(alvo['char'], nova_traducao)

if __name__ == "__main__":
    main()
