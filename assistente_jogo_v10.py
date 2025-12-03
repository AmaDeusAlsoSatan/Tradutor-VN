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
# SEU CAMINHO DO SCRIPT
ARQUIVO_JOGO = r"C:\Users\Defal\Documents\Projeto\Jogos\Hot_Cocoa_Magic-1.0-pc\game\tl\portuguese\script.rpy"

# CAMINHO DO ESPIÃO (Calculado automaticamente voltando pastas)
# Se o script está em game/tl/portuguese/script.rpy, a base está 3 níveis acima
PASTA_BASE_JOGO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(ARQUIVO_JOGO))))
ARQUIVO_VISUAL = os.path.join(PASTA_BASE_JOGO, "estado_visual.json")

ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_PRATA = "dataset_incubadora_silver.json"
ARQUIVO_IDENTIDADE = "identidade.json"

# MODELOS
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
    if texto.startswith('"') and texto.endswith('"'):
        texto = texto[1:-1]
    return texto.strip()

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f: json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_script():
    with open(ARQUIVO_JOGO, "r", encoding="utf-8") as f: return f.readlines()

def aprender_traducao(original, correcao):
    gold = carregar_json(ARQUIVO_OURO)
    silver = carregar_json(ARQUIVO_PRATA)
    
    silver = [item for item in silver if item['en'] != original]
    salvar_json(ARQUIVO_PRATA, silver)

    for item in gold:
        if item['en'] == original:
            item['pt'] = correcao
            item['score'] = 100.0
            item['contexto_vn'] = "Correcao_Assistente_V10"
            salvar_json(ARQUIVO_OURO, gold)
            return
    
    gold.append({"en": original, "pt": correcao, "score": 100.0, "contexto_vn": "Correcao_Assistente_V10"})
    salvar_json(ARQUIVO_OURO, gold)

def aprender_identidade(char_id):
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    if char_id in identidades: return
    print(f"\n🤔 Personagem novo: '{char_id}'")
    genero = input(f"Gênero? (M/F/N): ").strip().upper()
    if genero in ["M", "F", "N"]:
        identidades[char_id] = {"genero": genero, "obs": "Via Assistente V10"}
        salvar_json(ARQUIVO_IDENTIDADE, identidades)

# --- LÓGICA DO ESPIÃO VISUAL ---
def ler_estado_visual():
    """Lê o arquivo JSON gerado pelo jogo em tempo real"""
    if os.path.exists(ARQUIVO_VISUAL):
        try:
            with open(ARQUIVO_VISUAL, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def consultar_ia_opcoes(original, atual, contexto_bloco, char_id, identidades):
    if not configurar_ia(): return None, "Sem API.", ""
    print("   ...A IA está 'olhando' para a cena...")
    
    # 1. Pega dados de Identidade (Memória)
    info_char = ""
    if char_id in identidades:
        dados = identidades[char_id]
        info_char = f"PERSONAGEM FALANDO: '{char_id}' é {dados['genero']}."

    # 2. Pega dados Visuais (O Espião)
    dados_visuais = ler_estado_visual()
    info_visual = "VISUAL: Não disponível (Jogo fechado?)."
    
    if dados_visuais:
        qtd = dados_visuais.get("quantidade_pessoas", 0)
        quem_ta = ", ".join(dados_visuais.get("personagens_na_tela", []))
        info_visual = f"VISUAL (EM TEMPO REAL): Há {qtd} pessoas na tela. São elas: [{quem_ta}]."
        
        if qtd == 1:
            info_visual += " (DICA: Se falar 'Bem-vindos', use SINGULAR pois só tem 1 pessoa)."
        elif qtd > 1:
            info_visual += " (DICA: Pode ser Plural)."

    modelo = obter_modelo_seguro()
    
    prompt = f"""
    Atue como um Localizador de Jogos Profissional (EN -> PT-BR).
    
    --- CONTEXTO TÉCNICO ---
    {info_char}
    {info_visual}
    
    --- CONTEXTO NARRATIVO ---
    Trecho do Script:
    '''
    {contexto_bloco}
    '''
    
    --- ALVO ---
    Original (EN): "{original}"
    Tradução Atual (PT): "{atual}"
    
    TAREFA:
    Gere 3 opções de correção. Se o visual diz que só tem 1 pessoa, NÃO use plural. Se a personagem é Mulher, use feminino.
    
    FORMATO DE RESPOSTA (Estrito):
    OPCAO_1: [Tradução Literal]
    OPCAO_2: [Tradução Natural]
    OPCAO_3: [Transcriação Criativa]
    RECOMENDACAO: [1, 2 ou 3]
    EXPLICAÇÃO: [Por que escolheu essa opção baseada no Visual/Contexto]
    """
    
    try:
        res = modelo.generate_content(prompt).text
        
        opcoes = {}
        for i in range(1, 4):
            match = re.search(rf'OPCAO_{i}:\s*(.*)', res, re.IGNORECASE)
            if match: opcoes[str(i)] = limpar_markdown(match.group(1))
            
        rec = re.search(r'RECOMENDACAO:\s*(\d)', res, re.IGNORECASE)
        expl = re.search(r'EXPLICAÇÃO:\s*(.*)', res, re.IGNORECASE | re.DOTALL)
        
        melhor = rec.group(1) if rec else "2"
        motivo = limpar_markdown(expl.group(1)) if expl else ""
        
        return opcoes, melhor, motivo
        
    except Exception as e: return None, str(e), ""

def main():
    print("\n--- ASSISTENTE DE JOGO V10 (Com Visão Real) ---")
    
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
            print(f"\n[{n}] PT: {item['pt']}")
            print(f"    EN: {item['en']} ({item['char']})")
        
        while True:
            sel = input("\nQual linha? (Número) [Enter p/ cancelar]: ").strip()
            if not sel: 
                alvo = None
                break
            if sel.isdigit() and 0 <= int(sel) < len(encontrados):
                alvo = encontrados[int(sel)]
                break
        
        if not alvo: continue

        print(f"\n--- ANALISANDO LINHA {alvo['idx']+1} ---")
        
        inicio = max(0, alvo['idx'] - 10)
        fim = min(len(linhas), alvo['idx'] + 10)
        contexto_bloco = "".join(linhas[inicio:fim])
        
        opcoes, melhor, motivo = consultar_ia_opcoes(
            alvo['en'], alvo['pt'], contexto_bloco, alvo['char'], identidades
        )
        
        nova_traducao = ""
        
        if opcoes:
            print(f"\n💡 MOTIVO: {motivo}\n")
            for k, v in opcoes.items():
                destaque = "★ RECOMENDADA" if k == melhor else ""
                print(f" [{k}] {v}  {destaque}")
            print(" [4] Digitar minha versão")
            print(" [0] Cancelar")
            
            escolha = input("\nEscolha: ").strip()
            if escolha in opcoes: nova_traducao = opcoes[escolha]
            elif escolha == '4': nova_traducao = input("Digite: ")
        else:
            print(f"⚠️ Falha na IA: {melhor}") # Mostra o erro
            nova_traducao = input("Digite correção manual: ")

        if nova_traducao:
            indent = linhas[alvo['idx']].split('"')[0]
            if '"' in nova_traducao: nova_traducao = nova_traducao.replace('"', r'\"')
            linhas[alvo['idx']] = f'{indent}"{nova_traducao}"\n'
            with open(ARQUIVO_JOGO, "w", encoding="utf-8") as f: f.writelines(linhas)
            print(f"\n✅ Atualizado! Dê SHIFT+R.")
            
            en_limpo = alvo['en'].split('"')[1] if '"' in alvo['en'] else alvo['en']
            aprender_traducao(en_limpo, nova_traducao)
            if alvo['char'] != "?":
                aprender_identidade(alvo['char'])
                identidades = carregar_json(ARQUIVO_IDENTIDADE)

if __name__ == "__main__":
    main()
