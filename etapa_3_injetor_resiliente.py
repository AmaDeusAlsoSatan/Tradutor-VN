import json
import os
import time
import re
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script.rpy"
ARQUIVO_TEMP = "temp_dados.json"
ARQUIVO_OURO = "dataset_master_gold.json"
ARQUIVO_IDENTIDADE = "identidade.json"

# Configuração da API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    MODELO = 'models/gemini-2.0-flash'
else:
    MODELO = None

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try: return json.load(open(arquivo, "r", encoding="utf-8"))
        except: return {}
    return []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def limpar_markdown(texto):
    if not texto: return ""
    texto = texto.replace("**", "").replace("*", "").strip()
    if texto.startswith('"') and texto.endswith('"'): texto = texto[1:-1]
    return texto

def consultar_gemini_resiliente(item, identidades, visual_context):
    """Consulta o Gemini com paciência infinita e limitador de velocidade."""
    if not MODELO: return item['pt'], "Sem API"

    modelo = genai.GenerativeModel(MODELO)
    
    # Contexto
    char_id = item.get('char', '')
    info_char = ""
    if char_id in identidades:
        dados = identidades[char_id]
        info_char = f"PERSONAGEM: '{char_id}' é {dados.get('genero', '?')}."
    
    info_visual = ""
    if visual_context:
        info_visual = f"VISUAL: {', '.join(visual_context)}."

    prompt = f"""
    Atue como Editor de Localização (EN -> PT-BR).
    
    ORIGINAL: "{item['original']}"
    RASCUNHO (Annie): "{item['pt']}"
    
    CONTEXTO:
    {info_char}
    {info_visual}
    
    TAREFA:
    O rascunho está correto (gênero/contexto)? 
    Se sim, responda OK.
    Se não, reescreva APENAS a frase correta em Português.
    """

    # TENTATIVA COM RETRY (BACKOFF)
    for tentativa in range(5):
        try:
            # PAUSA OBRIGATÓRIA DE 4s PARA RESPEITAR LIMITE GRATUITO (15 RPM)
            time.sleep(4) 
            
            res = modelo.generate_content(prompt).text.strip()
            res_limpo = limpar_markdown(res)
            
            if res_limpo == "OK" or res_limpo == item['pt']:
                return item['pt'], "✅ Confirmado"
            else:
                return res_limpo, "✨ Melhorado"

        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str:
                print(f"\n   ⚠️ Cota excedida. Esperando 60s para esfriar... (Tentativa {tentativa+1}/5)")
                time.sleep(60) # Espera 1 minuto cheio
            else:
                print(f"\n   ❌ Erro IA: {e}. Usando rascunho.")
                return item['pt'], "Erro API"
    
    return item['pt'], "Timeout"

def main():
    print("\n--- ETAPA 3: INJETOR RESILIENTE (V11) ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: 'temp_dados.json' não encontrado. Rode a Etapa 1 primeiro.")
        return

    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)
    
    identidades = carregar_json(ARQUIVO_IDENTIDADE)
    
    # Carrega o arquivo de script original
    if os.path.exists(ARQUIVO_ALVO):
        with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
            linhas_arquivo = f.readlines()
    else:
        print(f"Erro: '{ARQUIVO_ALVO}' não encontrado.")
        return

    print(f"Total de linhas para processar: {len(tarefas)}")

    # --- FASE 1: INJEÇÃO DE SEGURANÇA (Garante que o arquivo não fique vazio) ---
    print("1. Aplicando tradução base (Annie) no arquivo...")
    count_base = 0
    for item in tarefas:
        idx = item.get('line_index')
        if idx is not None and idx < len(linhas_arquivo):
            trad_safe = item["pt"].replace('\n', r'\n').replace('"', r'\"')
            prefixo = f"{item.get('char', '')} " if item.get('char') else ""
            
            # Pega indentação original
            match_indent = re.match(r'^(\s*)', linhas_arquivo[idx])
            indent = match_indent.group(1) if match_indent else "    "
            
            linhas_arquivo[idx] = f'{indent}{prefixo}"{trad_safe}"\n'
            count_base += 1
            
    # Salva IMEDIATAMENTE a versão base
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(linhas_arquivo)
    print(f"   -> {count_base} linhas preenchidas com a tradução da Annie. O jogo já está jogável!")

    # --- FASE 2: REFINAMENTO COM IA (Lento e Seguro) ---
    print("\n2. Iniciando Refinamento com Gemini (Modo Resiliente)...")
    print("   (Isso vai demorar porque respeitamos o limite de velocidade do Google)")
    
    novos_aprendizados = []
    
    for i, item in enumerate(tarefas):
        # Pula se a Annie apenas copiou (...)
        if item['original'] == item['pt']: continue

        # Consulta Gemini com proteção 429
        visual = item.get('visual_context', [])
        trad_final, status = consultar_gemini_resiliente(item, identidades, visual)
        
        print(f"\rL{item.get('line_index')}: {status} | {trad_final[:40]}...", end="")

        # Se melhorou, atualiza o arquivo e salva no Ouro
        if status == "✨ Melhorado":
            idx = item.get('line_index')
            if idx is not None:
                trad_safe = trad_final.replace('\n', r'\n').replace('"', r'\"')
                prefixo = f"{item.get('char', '')} " if item.get('char') else ""
                match_indent = re.match(r'^(\s*)', linhas_arquivo[idx])
                indent = match_indent.group(1) if match_indent else "    "
                
                linhas_arquivo[idx] = f'{indent}{prefixo}"{trad_safe}"\n'
                
                # Salva no arquivo a cada alteração (Segurança máxima)
                with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
                    f.writelines(linhas_arquivo)

            # Guarda para aprendizado
            novos_aprendizados.append({
                "en": item["original"],
                "pt": trad_final,
                "score": 100.0,
                "contexto_vn": "Refinamento_Gemini"
            })

    # Salva aprendizado final
    if novos_aprendizados:
        gold = carregar_json(ARQUIVO_OURO)
        # Merge simples
        existentes = {x['en'] for x in gold}
        for n in novos_aprendizados:
            if n['en'] not in existentes:
                gold.append(n)
        salvar_json(ARQUIVO_OURO, gold)
        print(f"\n\n🧠 {len(novos_aprendizados)} frases melhoradas salvas no Cérebro!")

    print("\n✅ Processo 100% Concluído.")

if __name__ == "__main__":
    main()