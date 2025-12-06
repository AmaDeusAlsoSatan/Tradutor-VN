import os
import re

ARQUIVO_ALVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def main():
    print("--- CORRETOR V3 (RESET DE ASPAS) ---")
    
    # Use a mutable list for the target file path
    target_file = [ARQUIVO_ALVO]
    
    if not os.path.exists(target_file[0]):
        local_script = "script.rpy"
        if os.path.exists(local_script):
            target_file[0] = local_script
        else:
            print("Erro: Arquivo não encontrado.")
            return

    with open(target_file[0], "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    count = 0

    # Regex para separar: Indentação + Personagem + "Conteúdo"
    # Grupo 1: Indent + Char
    # Grupo 2: Conteúdo (incluindo aspas bagunçadas)
    regex_linha = re.compile(r'^(\s*(?:\w+\s+)?)\"(.*)\"\s*$')

    for linha in linhas:
        if linha.strip().startswith('#') or '"' not in linha:
            novas_linhas.append(linha)
            continue

        match = regex_linha.match(linha)
        if match:
            prefixo = match.group(1)
            conteudo_sujo = match.group(2)
            
            # LIMPEZA LÓGICA
            # 1. Removemos escapes de barra invertida nas aspas (\") -> (")
            conteudo_limpo = conteudo_sujo.replace('\\"', '"')
            
            # 2. Se a string começou com aspas extras por causa do erro anterior, removemos
            # Ex: "Texto" -> Texto
            if conteudo_limpo.startswith('"') and conteudo_limpo.endswith('"'):
                conteudo_limpo = conteudo_limpo[1:-1]
            
            # 3. Agora escapamos APENAS as aspas internas reais
            # Ex: Ele disse "Oi" -> Ele disse \"Oi\"
            conteudo_final = conteudo_limpo.replace('"', r'\"')
            
            # 4. Reconstrói: Prefixo "Conteúdo" \n
            nova_linha = f'{prefixo}"{conteudo_final}"\n'
            
            if nova_linha != linha:
                count += 1
                novas_linhas.append(nova_linha)
            else:
                novas_linhas.append(linha)
        else:
            # Caso não case no regex (ex: aspas triplas ou linhas quebradas), mantém
            novas_linhas.append(linha)

    with open(target_file[0], "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ {count} linhas foram normalizadas. Tente abrir o jogo agora!")

if __name__ == "__main__":
    main()
