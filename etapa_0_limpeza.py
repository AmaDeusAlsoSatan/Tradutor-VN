import os
import re

ARQUIVO_ALVO = "script.rpy"

def main():
    print("--- ETAPA 0: FAXINA DE ARQUIVO ---")
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: script.rpy não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    removidas = 0

    # Regex para detectar linhas de diálogo que NÃO estão vazias
    # Ex: m "Texto" (Captura) vs m "" (Ignora)
    regex_cheio = re.compile(r'^\s*(?:.+?\s+)?\"(.+)\"') 

    for linha in linhas:
        linha_strip = linha.strip()
        
        # Se for comentário (#), mantém (É a nossa fonte em Inglês!)
        if linha_strip.startswith('#'):
            novas_linhas.append(linha)
            continue
        
        # Se for linha de código...
        match = regex_cheio.match(linha)
        if match:
            # Se tem texto dentro das aspas, é a tradução velha/errada. LIXO!
            # Mas cuidado para não apagar configurações do sistema
            if "translate" in linha or "style" in linha:
                novas_linhas.append(linha)
            else:
                # É diálogo preenchido. Apaga!
                removidas += 1
                continue
        else:
            # Se for linha vazia (m "") ou outra coisa, mantém.
            novas_linhas.append(linha)

    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"Limpeza concluída! {removidas} linhas de tradução antiga removidas.")
    print("Agora seu arquivo está PURO (Inglês no comentário, Vazio no código).")

if __name__ == "__main__":
    main()
