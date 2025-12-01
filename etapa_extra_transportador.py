import os
import re

# CONFIG
ARQUIVO_ALVO = "script_novo_jogo.rpy"

def main():
    print("--- INICIANDO O TRANSPORTADOR DE TRADUÇÃO ---")
    print(f"Lendo: {ARQUIVO_ALVO}")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: Arquivo não encontrado.")
        return

    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    novas_linhas = []
    # Regex para capturar o conteúdo dentro das aspas do comentário
    # Captura: # personagem "Texto"
    regex_origem = re.compile(r'^\s*#\s*(?:.+?\s+)?\"(.*)\"')
    
    # Regex para identificar a linha de destino (vazia ou não)
    # Captura: personagem ""
    regex_destino = re.compile(r'^(\s*)(?:.+?\s+)?\"(.*)\"')

    buffer_texto = None
    contador = 0

    for i, linha in enumerate(linhas):
        linha_strip = linha.strip()
        
        # 1. É uma linha de comentário (Fonte)?
        if linha_strip.startswith('#'):
            match = regex_origem.match(linha)
            if match:
                # Guardamos o texto que está no comentário
                buffer_texto = match.group(1)
            novas_linhas.append(linha)
            continue

        # 2. É uma linha de código (Destino)?
        match_dest = regex_destino.match(linha)
        if match_dest and buffer_texto is not None:
            # Se encontramos uma linha de diálogo e temos um texto guardado...
            indentacao = match_dest.group(1)
            
            # Reconstrói a linha usando o texto do comentário!
            # Mantém a parte antes das aspas (nome do personagem) intacta
            parte_antes_aspas = linha.split('"')[0]
            
            # Monta a nova linha: Indentação + Nome + "Texto do Comentário"
            nova_linha = f'{parte_antes_aspas}"{buffer_texto}"\n'
            
            novas_linhas.append(nova_linha)
            contador += 1
            buffer_texto = None # Já usamos, limpa o buffer
        else:
            # Linha comum (código, menus, etc), mantém igual
            novas_linhas.append(linha)
            # Se não usou o buffer imediatamente, descarta para evitar erros
            if not linha_strip.startswith('translate'): 
                buffer_texto = None

    # Salva o arquivo corrigido
    with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"\nSUCESSO! {contador} linhas foram transportadas dos comentários para o jogo.")
    print("Agora você pode colocar o arquivo na pasta 'game/tl/portuguese' e testar.")

if __name__ == "__main__":
    main()
