import os
import re

# SEU CAMINHO COMPLETO
ARQUIVO_ALVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def main():
    print("--- CORRETOR V4 (RECONSTRUÇÃO DEFINITIVA) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        if os.path.exists("script.rpy"):
            ARQUIVO_ALVO = "script.rpy"
            print("Usando script.rpy local.")
        else:
            print("Erro: Arquivo não encontrado.")
            return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    count = 0

    # Regex para capturar: (Indentação) (Personagem opcional) " (Conteúdo) "
    # Este regex é mais permissivo para capturar linhas mal formadas
    regex_linha = re.compile(r'^(\s*(?:\w+\s+)?)(["\'].*["\'])\s*$')

    for linha in linhas:
        # Ignora comentários e linhas vazias
        if linha.strip().startswith('#') or not linha.strip():
            novas_linhas.append(linha)
            continue

        match = regex_linha.match(linha)
        if match:
            prefixo = match.group(1)
            conteudo_bruto = match.group(2)
            
            # Remove aspas externas (podem ser simples, duplas ou triplas)
            if conteudo_bruto.startswith('"""') and conteudo_bruto.endswith('"""'):
                conteudo_limpo = conteudo_bruto[3:-3]
            elif conteudo_bruto.startswith("'''") and conteudo_bruto.endswith("'''"):
                conteudo_limpo = conteudo_bruto[3:-3]
            elif conteudo_bruto.startswith('"') and conteudo_bruto.endswith('"'):
                conteudo_limpo = conteudo_bruto[1:-1]
            elif conteudo_bruto.startswith("'") and conteudo_bruto.endswith("'"):
                conteudo_limpo = conteudo_bruto[1:-1]
            else:
                # Se não casar com nenhum padrão conhecido, mantém como está (segurança)
                novas_linhas.append(linha)
                continue

            # CORREÇÃO DE ESCAPES
            # 1. Desescapar tudo primeiro para ter o texto "cru"
            #    (Isso corrige casos de dupla escapagem como \\")
            conteudo_cru = conteudo_limpo.replace('\\"', '"').replace("\\'", "'")
            
            # 2. Escapar APENAS aspas duplas, pois vamos usar aspas duplas para envolver a string
            conteudo_final = conteudo_cru.replace('"', r'\"')
            
            # 3. Garantir que newlines sejam escapados
            conteudo_final = conteudo_final.replace('\n', r'\n')

            # Reconstrói a linha: Prefixo "Conteúdo" \n
            nova_linha = f'{prefixo}"{conteudo_final}"\n'
            
            if nova_linha != linha:
                count += 1
                novas_linhas.append(nova_linha)
            else:
                novas_linhas.append(linha)
        else:
            # Caso não seja uma linha de diálogo reconhecível, mantém
            novas_linhas.append(linha)

    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ {count} linhas foram reconstruídas e sanitizadas.")

if __name__ == "__main__":
    main()
