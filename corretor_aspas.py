import os
import re

ARQUIVO_ALVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def main():
    print("--- CIRURGIA DE ASPAS DUPLAS ---")
    
    # Esta variável local é necessária para que possamos modificá-la
    arquivo_alvo_local = ARQUIVO_ALVO

    if not os.path.exists(arquivo_alvo_local):
        # Tenta achar no diretório local se o caminho absoluto falhar
        if os.path.exists("script.rpy"):
            arquivo_alvo_local = "script.rpy"
        else:
            print(f"Erro: Arquivo não encontrado em '{ARQUIVO_ALVO}' ou no diretório local.")
            return

    with open(arquivo_alvo_local, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    correcoes = 0

    # Regex para identificar linhas com aspas duplas escapadas nas pontas
    # Ex: " \"Texto\" "  -> Queremos virar -> "Texto"
    padrao_erro = re.compile(r'^(\s*)(?:(\w+)\s+)?\"\\\"(.*)\\\"\"\s*$')

    for linha in linhas:
        match = padrao_erro.match(linha)
        if match:
            indent = match.group(1)
            char = match.group(2) if match.group(2) else ""
            conteudo = match.group(3)
            
            # Reconstrói a linha limpa
            prefixo = f"{char} " if char else ""
            # Removemos os escapes internos (\") que sobrarem, se houverem
            conteudo_limpo = conteudo.replace('\\"', '"') 
            # E escapamos apenas as aspas que fazem parte do texto mesmo
            conteudo_safe = conteudo_limpo.replace('"', r'\"')
            
            nova_linha = f'{indent}{prefixo}"{conteudo_safe}"\n'
            novas_linhas.append(nova_linha)
            correcoes += 1
        else:
            # Tenta pegar casos onde a aspa não está escapada mas está dupla
            # Ex: ""Texto""
            if '""' in linha and not '"""' in linha: # Ignora triplas
                 nova_linha = linha.replace('""', '"')
                 if nova_linha != linha:
                     novas_linhas.append(nova_linha)
                     correcoes += 1
                 else:
                     novas_linhas.append(linha)
            else:
                novas_linhas.append(linha)

    with open(arquivo_alvo_local, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"Cirurgia concluída! {correcoes} linhas corrigidas em '{arquivo_alvo_local}'.")

if __name__ == "__main__":
    main()