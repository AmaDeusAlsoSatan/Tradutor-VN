import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURAÇÃO ---
ARQUIVO_ALVO = "script.rpy"
ARQUIVO_TEMP = "temp_dados.json"
ARQUIVO_SNOWBALL = "dataset_master_gold.json" # Já salva direto no Ouro se o Gemini aprovar

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODELO = 'models/gemini-2.0-flash'

def main():
    print("\n--- ETAPA 3: SUPERVISOR VISUAL (Gemini) ---")
    
    if not os.path.exists(ARQUIVO_TEMP):
        print("Erro: Rode a Etapa 1 V10 primeiro.")
        return

    with open(ARQUIVO_TEMP, "r", encoding="utf-8") as f:
        tarefas = json.load(f)
    
    print(f"Analisando {len(tarefas)} linhas com IA...")
    
    modelo = genai.GenerativeModel(MODELO)
    
    novos_aprendizados = []
    linhas_arquivo = open(ARQUIVO_ALVO, "r", encoding="utf-8").readlines()

    # Processa em lotes para ser rápido? Não, vamos um por um para garantir qualidade máxima nesta fase.
    # O Gemini Flash é rápido o suficiente.
    
    for i, item in enumerate(tarefas):
        # Pula se a Annie apenas copiou (...)
        if item["original"] == item["pt"]: continue

        # Monta o contexto visual para o Gemini
        quem_fala = item["char"]
        visuais = ", ".join(item["visual_context"])
        
        prompt = f"""
        Você é um Supervisor de Tradução de Visual Novels.
        
        CENA:
        Personagens na tela: [{visuais}]
        Quem está falando: \'{quem_fala}\'
        
        ANÁLISE:
        Original (EN): "{item["original"]}"
        Tradução (PT): "{item["pt"]}"
        
        TAREFA:
        A tradução respeita o gênero e número baseados na cena? 
        (Ex: Se tem 1 pessoa, \'Bem-vindos\' está errado. Se o falante é mulher, \'Obrigado\' está errado).
        
        Se estiver ÓTIMA, responda apenas: OK
        Se precisar corrigir, responda apenas a NOVA FRASE.
        """
        
        try:
            res = modelo.generate_content(prompt).text.strip()
            
            # Remove aspas se a IA colocou
            if res.startswith("\"") and res.endswith("\""): res = res[1:-1]
            
            if res == "OK" or res == item["pt"]:
                status = "✅"
                final = item["pt"]
            else:
                status = "✨ CORRIGIDO"
                final = res
                
            print(f"\rL{item["line_index"]}: {status} | {final[:40]}...", end="")
            
            # Atualiza a tarefa com a versão final
            item["pt"] = final
            
            # Salva no Gold (já que passou pelo crivo do Gemini)
            novos_aprendizados.append({"en": item["original"], "pt": final, "score": 100, "contexto": "Supervisor_V10"})

            # Injeta no arquivo imediatamente (Memória RAM)
            idx = item["line_index"]
            if idx < len(linhas_arquivo):
                trad_safe = final.replace("\n", "\\n").replace("\"", r"\"")
                prefixo = f"{item["char"]} " if item["char"] else ""
                # Mantém indentação
                indent = linhas_arquivo[idx].split("\"")[0] if "\"" in linhas_arquivo[idx] else item["indent"]
                linhas_arquivo[idx] = f'{indent}"{trad_safe}"\n'

        except Exception as e:
            print(f" Erro IA: {e}")

    # Salva arquivo final
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(linhas_arquivo)
        
    # Salva aprendizado
    if novos_aprendizados:
        lista = []
        if os.path.exists(ARQUIVO_SNOWBALL):
            try: lista = json.load(open(ARQUIVO_SNOWBALL, "r", encoding="utf-8"))
            except: pass
        
        # Merge simples
        existentes = {x["en"] for x in lista}
        for n in novos_aprendizados:
            if n["en"] not in existentes:
                lista.append(n)
        
        with open(ARQUIVO_SNOWBALL, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=4, ensure_ascii=False)
            
    print(f"\n\nProcesso finalizado. {len(novos_aprendizados)} frases validadas/corrigidas.")

if __name__ == "__main__":
    main()
