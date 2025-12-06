import os

ARQUIVO_ALVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def main():
    print("--- CORRETOR FINAL (FORÇA BRUTA) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: Arquivo não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    count = 0

    for linha in linhas:
        if '"' not in linha or linha.strip().startswith("#"):
            novas_linhas.append(linha)
            continue

        # Lógica de substituição direta
        linha_original = linha
        linha_modificada = linha.replace('\\"', '"') # Desescapa tudo

        # Encontra o prefixo e o conteúdo
        partes = linha_modificada.split('"')
        if len(partes) >= 3:
            prefixo = partes[0]
            conteudo = '"'.join(partes[1:-1])
            sufixo = partes[-1]

            # Remove aspas duplas das bordas do conteúdo
            while conteudo.startswith('"') and conteudo.endswith('"'):
                conteudo = conteudo[1:-1]
            
            # Re-escapa as aspas internas
            conteudo = conteudo.replace('"', '\\"')

            linha_modificada = f'{prefixo}"{conteudo}"{sufixo}'

        if linha_modificada != linha_original:
            count += 1
        
        novas_linhas.append(linha_modificada)

    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ {count} linhas foram processadas. Tente abrir o jogo agora!")

if __name__ == "__main__":
    main()
