import os

ARQUIVO = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy" # Ajuste o caminho se necessário

def corrigir_duplo_escape():
    if not os.path.exists(ARQUIVO):
        print(f"Arquivo não encontrado: {ARQUIVO}")
        return

    with open(ARQUIVO, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # O problema é a barra dupla antes da aspa. Vamos trocar por barra simples.
    # No Python, para representar \\" string, precisamos escrever quatro barras no código ou usar raw string
    # Mas aqui simplificamos: buscamos o padrão literal de texto.
    
    novo_conteudo = conteudo.replace("\\\\\"", "\\\"")
    
    if novo_conteudo != conteudo:
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            f.write(novo_conteudo)
        print("✅ Correção aplicada: \\\" substituído por \"")
    else:
        print("ℹ️ Nenhuma ocorrência de \\\" encontrada.")

if __name__ == "__main__":
    corrigir_duplo_escape()
