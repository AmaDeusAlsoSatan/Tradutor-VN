import os
import json
import tokenize
import re
from io import BytesIO
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# CONFIG
ARQUIVO_ALVO = "script.rpy"
CAMINHO_MODELO = "./modelo_annie_v1"
ARQUIVO_TEMP = "temp_dados.json"

def gerador_linhas_logicas(caminho_arquivo):
    """Lê o arquivo respeitando a lógica do RenPy (PDF Solution)"""
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas_fisicas = f.readlines()

    buffer = []
    profundidade = 0

    for linha in linhas_fisicas:
        linha_limpa = linha.strip()
        if not linha_limpa and profundidade == 0 and not buffer: continue

        conteudo = linha_limpa.split('#')[0] # Ignora comentários na contagem
        profundidade += conteudo.count('(') - conteudo.count(')')
        profundidade += conteudo.count('[') - conteudo.count(']')
        profundidade += conteudo.count('{') - conteudo.count('}')

        buffer.append(linha)

        if profundidade == 0 and not linha_limpa.endswith('\\'):
            yield "".join(buffer)
            buffer = []
            profundidade = 0
            
    if buffer: yield "".join(buffer)

def analisar_linha_renpy_v6(linha_logica):
    """Tokenizador V6 (PDF Solution)"""
    linha_limpa = linha_logica.strip()
    if linha_limpa.startswith('#'): linha_limpa = linha_limpa[1:].strip()
    if not linha_limpa: return None, None, None

    try:
        tokens = list(tokenize.tokenize(BytesIO(linha_limpa.encode('utf-8')).readline))
    except: return None, None, None

    tokens_uteis = [t for t in tokens if t.type not in (tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.COMMENT)]
    if not tokens_uteis: return None, None, None

    indice = -1
    nivel = 0
    for i, token in enumerate(tokens_uteis):
        if token.type == tokenize.OP:
            if token.string in '([{': nivel += 1
            elif token.string in ')]}': nivel -= 1
        if nivel == 0 and token.type == tokenize.STRING:
            indice = i
            break
    
    if indice == -1: return None, None, None

    quem = tokenize.untokenize(tokens_uteis[:indice]).strip()
    conteudo_bruto = tokens_uteis[indice].string
    
    # Limpeza de aspas
    if len(conteudo_bruto) >= 6 and (conteudo_bruto.startswith('"""') or conteudo_bruto.startswith("'''")):
         conteudo = conteudo_bruto[3:-3]
    elif len(conteudo_bruto) >= 2:
         conteudo = conteudo_bruto[1:-1]
    else: conteudo = ""

    indent = ""
    for char in linha_logica:
        if char.isspace(): indent += char
        else: break

    return indent, quem, conteudo

def precisa_traduzir(texto):
    """VACINA ANTI-ALUCINAÇÃO: Só traduz se tiver pelo menos 2 letras."""
    if len(re.findall(r'[a-zA-Z]', texto)) < 2:
        return False
    return True

def main():
    print("\n--- ETAPA 1: TRADUÇÃO (V9 - Definitiva) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print("Erro: Arquivo alvo não encontrado.")
        return

    tarefas = []
    # Usando o Agregador do PDF
    iterador = gerador_linhas_logicas(ARQUIVO_ALVO)
    
    print("Mapeando linhas...")
    # Como o iterador muda o índice das linhas, precisamos rastrear a linha física manualmente
    # Vamos ler o arquivo físico novamente só para ter os índices corretos para injeção
    with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
        linhas_fisicas_raw = f.readlines()
        
    # Mapa de Texto Original -> Índice Físico
    # (Estratégia simplificada: Varredura sequencial)
    cursor_fisico = 0
    
    buffer_original = None
    
    # Recriamos o iterador para processamento
    iterador = gerador_linhas_logicas(ARQUIVO_ALVO)

    for linha_logica in iterador:
        # Acha onde essa linha lógica está no arquivo físico
        # (Isso é uma aproximação, mas funciona para arquivos padrão RenPy)
        while cursor_fisico < len(linhas_fisicas_raw):
            if linhas_fisicas_raw[cursor_fisico].strip() in linha_logica:
                break
            cursor_fisico += 1
            
        # Processamento
        if '"' not in linha_logica and "'" not in linha_logica: continue
        
        eh_comentario = linha_logica.strip().startswith('#')
        indent, quem, texto = analisar_linha_renpy_v6(linha_logica)
        
        if texto is not None:
            texto = texto.replace('\\n', '\n')
            
            if eh_comentario:
                if "script.rpy" not in linha_logica:
                    buffer_original = texto
            else:
                if buffer_original is not None:
                    # Se for vazio OU igual ao original (cópia), traduzir
                    if texto == "" or texto == buffer_original:
                        tarefas.append({
                            "line_index": cursor_fisico, # Índice aproximado para ordenação
                            "original": buffer_original,
                            "indent": indent,
                            "char": quem
                        })
                    buffer_original = None
        
        cursor_fisico += 1

    print(f"Linhas para traduzir: {len(tarefas)}")
    
    # Tradução Neural
    print("Carregando modelo...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
        model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)
    except: return

    print("Traduzindo e Filtrando...")
    cont_pulados = 0
    
    for i, item in enumerate(tarefas):
        original = item["original"]
        
        # APLICA A VACINA
        if not precisa_traduzir(original):
            item["pt"] = original # Copia o original (...)
            cont_pulados += 1
        else:
            inputs = tokenizer(">>pt<< " + original, return_tensors="pt", padding=True)
            out = model.generate(**inputs, max_length=128, num_beams=4)
            item["pt"] = tokenizer.decode(out[0], skip_special_tokens=True)
            
        print(f"\rProcessado: {i+1}/{len(tarefas)} (Mantidos originais: {cont_pulados})", end="")

    with open(ARQUIVO_TEMP, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, indent=4)
    
    print("\nEtapa 1 Concluída.")

if __name__ == "__main__":
    main()
