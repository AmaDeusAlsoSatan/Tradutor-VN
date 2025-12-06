import os

# SEU CAMINHO COMPLETO
ARQUIVO_ALVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def main():
    print("--- CORRETOR DE ASPAS V2 (RECONSTRUÇÃO) ---")
    
    # Esta variável local é necessária para que possamos modificá-la
    arquivo_alvo_local = ARQUIVO_ALVO
    
    if not os.path.exists(arquivo_alvo_local):
        print(f"Erro: Arquivo não encontrado: {arquivo_alvo_local}")
        # Tenta local
        if os.path.exists("script.rpy"):
            arquivo_alvo_local = "script.rpy"
            print("Usando script.rpy local.")
        else:
            return

    with open(arquivo_alvo_local, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    count = 0

    for linha in linhas:
        # Só mexe em linhas de diálogo (que têm aspas e não são comentários)
        if '"' in linha and not linha.strip().startswith('#'):
            # Separa a indentação/personagem do conteúdo
            # Ex: '    m "Texto"' -> prefixo='    m ', resto='"Texto"\n'
            try:
                # Acha a primeira aspa
                idx_primeira_aspa = linha.find('"')
                prefixo = linha[:idx_primeira_aspa]
                
                # Pega todo o conteúdo a partir da primeira aspa, removendo espaços e quebra de linha do final
                conteudo_bruto = linha[idx_primeira_aspa:].strip()
                
                # LIMPEZA PROFUNDA
                # 1. Remove aspas das pontas se existirem (quantas tiverem)
                conteudo_limpo = conteudo_bruto.strip('"')
                
                # 2. Remove escapes de aspas que sobraram nas pontas (\")
                if conteudo_limpo.startswith('\\"'):
                    conteudo_limpo = conteudo_limpo[2:]
                if conteudo_limpo.endswith('\\"'):
                    conteudo_limpo = conteudo_limpo[:-2]
                
                # 3. Limpa escapes internos desnecessários (opcional, mas bom)
                # Transforma \" no meio do texto em " simples, depois re-escapa se precisar
                # Mas para segurança, vamos apenas garantir que a linha final esteja certa.
                
                # 4. Reconstrói a linha: Prefixo + " + Conteúdo + " + \n
                # O Python vai garantir que aspas internas sejam tratadas se usarmos repr? Não, vamos manual.
                
                # Se houver aspas duplas DENTRO do texto, elas precisam virar \"
                conteudo_final = conteudo_limpo.replace('"', r'\"')
                
                # Desfaz a dupla escapada caso tenhamos criado \\" onde já era \"
                # (Caso o texto já estivesse certo)
                conteudo_final = conteudo_final.replace(r'\\"', r'\"')

                nova_linha = f'{prefixo}"{conteudo_final}"\n'
                
                if nova_linha != linha:
                    count += 1
                    novas_linhas.append(nova_linha)
                else:
                    novas_linhas.append(linha)
            except:
                # Se der erro na lógica, mantém a linha original para não destruir o arquivo
                novas_linhas.append(linha)
        else:
            novas_linhas.append(linha)

    with open(arquivo_alvo_local, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ Processo finalizado. {count} linhas foram reconstruídas.")

if __name__ == "__main__":
    main()