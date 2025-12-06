import os
import re

# Caminho do arquivo
ARQUIVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

def corrigir_linha(linha):
    """Corrige padrões problemáticos de aspas em uma linha"""
    
    # Se não tem aspas ou é comentário, retorna sem modificar
    if '"' not in linha or linha.strip().startswith('#'):
        return linha
    
    # Padrão 1: Linhas que começam com "\\" após o primeiro "
    # Ex: "\\Texto\" -> "Texto"
    padrao1 = re.compile(r'^(\s*)([a-z]\s+)?"\\\\(.*)\\"?\s*$')
    match1 = padrao1.match(linha)
    if match1:
        indent = match1.group(1)
        char = match1.group(2) or ""
        conteudo = match1.group(3)
        return f'{indent}{char}"{conteudo}"\n'
    
    # Padrão 2: Aspas escapadas desnecessárias no início e fim
    # Ex: "\"Texto\"" -> "Texto"
    padrao2 = re.compile(r'^(\s*)([a-z]\s+)?"\\"(.*)\\""\s*$')
    match2 = padrao2.match(linha)
    if match2:
        indent = match2.group(1)
        char = match2.group(2) or ""
        conteudo = match2.group(3)
        # Escapa apenas aspas internas que são parte do texto
        conteudo = conteudo.replace(r'\"', '"').replace('"', r'\"')
        return f'{indent}{char}"{conteudo}"\n'
    
    # Padrão 3: Aspas duplas vazias no final
    # Ex: "Texto"" -> "Texto"
    if linha.rstrip().endswith('""'):
        linha = linha.rstrip()[:-1] + '\n'
    
    return linha

def main():
    print("=== CORRETOR DE ASPAS DEFINITIVO ===\n")
    
    # Verifica se arquivo existe
    arquivo_path = ARQUIVO
    if not os.path.exists(arquivo_path):
        if os.path.exists("script.rpy"):
            arquivo_path = "script.rpy"
            print("Usando script.rpy do diretório atual")
        else:
            print(f"❌ Arquivo não encontrado: {ARQUIVO}")
            return
    
    # Lê o arquivo
    print(f"📖 Lendo arquivo: {arquivo_path}")
    with open(arquivo_path, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    
    print(f"   Total de linhas: {len(linhas)}")
    
    # Processa cada linha
    linhas_corrigidas = []
    contador = 0
    
    for i, linha in enumerate(linhas, 1):
        linha_nova = corrigir_linha(linha)
        if linha_nova != linha:
            contador += 1
            # Mostra algumas correções como exemplo
            if contador <= 5:
                print(f"\n📝 Linha {i} corrigida:")
                print(f"   Antes: {linha.rstrip()[:80]}")
                print(f"   Depois: {linha_nova.rstrip()[:80]}")
        linhas_corrigidas.append(linha_nova)
    
    # Salva o arquivo corrigido
    print(f"\n💾 Salvando correções...")
    with open(arquivo_path, "w", encoding="utf-8") as f:
        f.writelines(linhas_corrigidas)
    
    print(f"\n✅ Concluído!")
    print(f"   {contador} linhas foram corrigidas")
    print(f"\n🎮 Agora tente abrir o jogo novamente!")

if __name__ == "__main__":
    main()
