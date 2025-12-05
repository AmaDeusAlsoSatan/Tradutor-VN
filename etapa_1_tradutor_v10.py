import os
import json
import re
import tokenize
from io import BytesIO
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# --- CONFIGURAÇÕES ---
ARQUIVO_ALVO = "script.rpy" # Certifique-se que este é o da VN 3!
CAMINHO_MODELO = "./modelo_annie_v1"
ARQUIVO_TEMP = "temp_dados.json"

# Regex para capturar comandos visuais do Ren'Py
REGEX_SHOW = re.compile(r'^\s*show\s+(\w+)')
REGEX_SCENE = re.compile(r'^\s*scene\s+(\w+)')
REGEX_HIDE = re.compile(r'^\s*hide\s+(\w+)')

def gerador_linhas_logicas(caminho_arquivo):
    """Lê o arquivo respeitando a lógica do RenPy (PDF Solution)"""
    if not os.path.exists(caminho_arquivo): return []
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas_fisicas = f.readlines()

    buffer = []
    profundidade = 0

    for linha in linhas_fisicas:
        linha_limpa = linha.strip()
        if not linha_limpa and profundidade == 0 and not buffer: continue

        conteudo = linha_limpa.split('#')[0]
        profundidade += conteudo.count('(') - conteudo.count(')')
        profundidade += conteudo.count('[') - conteudo.count(']')
        profundidade += conteudo.count('{') - conteudo.count('}')

        buffer.append(linha)

        if profundidade == 0 and not linha_limpa.endswith('\\'):
            yield "".join(buffer)
            buffer = []
            profundidade = 0
            
    if buffer: yield "".join(buffer)

def analisar_linha_renpy(linha):
    """Tokenizador V6 para extrair texto"""
    linha_limpa = linha.strip()
    if linha_limpa.startswith('#'): linha_limpa = linha_limpa[1:].strip()
    if not linha_limpa: return None, None, None

    try:
        tokens = list(tokenize.tokenize(BytesIO(linha_limpa.encode('utf-8')).readline))
    except: return None, None, None

    tokens = [t for t in tokens if t.type not in (tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.COMMENT)]
    if not tokens: return None, None, None

    indice = -1
    nivel = 0
    for i, token in enumerate(tokens):
        if token.type == tokenize.OP:
            if token.string in '([{': nivel += 1
            elif token.string in ')]}': nivel -= 1
        if nivel == 0 and token.type == tokenize.STRING:
            indice = i
            break
    
    if indice == -1: return None, None, None

    quem = tokenize.untokenize(tokens[:indice]).strip()
    conteudo = tokens[indice].string
    
    if len(conteudo) >= 6 and (conteudo.startswith('"""') or conteudo.startswith("'''")):
         conteudo = conteudo[3:-3]
    elif len(conteudo) >= 2:
         conteudo = conteudo[1:-1]

    # Captura indentação
    match_indent = re.match(r'^(\s*)', linha)
    indent = match_indent.group(1) if match_indent else ""

    return indent, quem, conteudo

def precisa_traduzir(texto):
    if len(re.findall(r'[a-zA-Z]', texto)) < 2: return False
    return True

def main():
    print("\n--- ETAPA 1: TRADUÇÃO V10 (Annie + Olho Digital) ---")
    
    if not os.path.exists(ARQUIVO_ALVO):
        print(f"Erro: '{ARQUIVO_ALVO}' não encontrado.")
        return

    # 1. Mapeamento e Rastreamento Visual
    tarefas = []
    personagens_na_tela = set() # O "Olho" do código
    
    print("Mapeando script e rastreando imagens...")
    
    # Precisamos ler linha a linha para manter o estado visual sincronizado
    # O gerador de linhas lógicas é ótimo para texto, mas para 'show/hide' precisamos ver onde elas ocorrem
    # Vamos usar uma abordagem híbrida: ler o arquivo físico para rastrear imagens, e o lógico para extrair texto.
    
    # Simplificação V10: Vamos ler tudo sequencialmente.
    iterador = gerador_linhas_logicas(ARQUIVO_ALVO)
    
    for i, linha_logica in enumerate(iterador):
        linha_lower = linha_logica.lower().strip()
        
        # --- LÓGICA DO ESPIÃO VISUAL ---
        # Atualiza quem está na tela ANTES de processar o diálogo
        if linha_lower.startswith("scene "):
            # Scene limpa tudo e põe um novo fundo
            personagens_na_tela.clear()
            match = REGEX_SCENE.match(linha_lower)
            if match: personagens_na_tela.add(match.group(1))
            
        elif linha_lower.startswith("show "):
            # Show adiciona alguém
            match = REGEX_SHOW.match(linha_lower)
            if match: personagens_na_tela.add(match.group(1))
            
        elif linha_lower.startswith("hide "):
            # Hide remove alguém
            match = REGEX_HIDE.match(linha_lower)
            if match and match.group(1) in personagens_na_tela:
                personagens_na_tela.remove(match.group(1))
        
        # --- LÓGICA DE EXTRAÇÃO ---
        # (Verifica par original/tradução) - Simplificado para "Tradução Nova"
        # Assume que estamos traduzindo um arquivo gerado pelo RenPy (Original no comentário #)
        
        if '"' not in linha_logica and "'" not in linha_logica: continue
        
        # Se for comentário (#), é o nosso original em inglês
        if linha_logica.strip().startswith('#') and "script.rpy" not in linha_logica:
             _, quem_orig, texto_orig = analisar_linha_renpy(linha_logica)
             if texto_orig:
                 # Achamos um original! Vamos ver se a próxima linha é a tradução vazia
                 # (Essa lógica requer state machine, vamos simplificar:
                 # Guardamos o original e esperamos a próxima iteração)
                 pass 
                 # Nota: O Agregador Lógico dificulta pegar o par # e codigo se eles forem iterados separadamente.
                 # Vamos usar a estratégia de "Buffer" dentro do loop único.
    
    # --- RE-IMPLEMENTAÇÃO ROBUSTA COM BUFFER E VISUAL ---
    # Resetamos para fazer direito
    iterador = gerador_linhas_logicas(ARQUIVO_ALVO)
    buffer_original = None
    personagens_na_tela = set()
    
    linhas_fisicas_raw = open(ARQUIVO_ALVO, "r", encoding="utf-8").readlines()
    cursor_fisico = 0
    
    print("   ...Processando contexto visual...")

    for linha_logica in iterador:
        # Sincronia aproximada com linha física para injeção
        # (Apenas para ter um ID sequencial)
        while cursor_fisico < len(linhas_fisicas_raw):
            if linhas_fisicas_raw[cursor_fisico].strip() in linha_logica:
                break
            cursor_fisico += 1
            
        # --- ATUALIZAÇÃO VISUAL ---
        ll = linha_logica.strip()
        if ll.startswith("scene "): 
            personagens_na_tela.clear()
            m = REGEX_SCENE.match(ll)
            if m: personagens_na_tela.add(m.group(1))
        elif ll.startswith("show "):
            m = REGEX_SHOW.match(ll)
            if m: personagens_na_tela.add(m.group(1))
        elif ll.startswith("hide "):
            m = REGEX_HIDE.match(ll)
            if m and m.group(1) in personagens_na_tela:
                personagens_na_tela.remove(m.group(1))

        # --- EXTRAÇÃO ---
        if '"' not in linha_logica: 
            cursor_fisico += 1
            continue
            
        eh_comentario = ll.startswith('#')
        indent, quem, texto = analisar_linha_renpy(linha_logica)
        
        if texto is not None:
            texto = texto.replace('\\n', '\n')
            if eh_comentario:
                if "script.rpy" not in linha_logica:
                    buffer_original = texto
            else:
                # É linha de código. Tem original esperando?
                if buffer_original:
                    if texto == "" or texto == buffer_original:
                        # AQUI ESTÁ A MÁGICA: Salvamos quem está na tela junto com a frase!
                        tarefas.append({
                            "line_index": cursor_fisico,
                            "original": buffer_original,
                            "indent": indent,
                            "char": quem,
                            "visual_context": list(personagens_na_tela) # O Olho Digital
                        })
                    buffer_original = None
        
        cursor_fisico += 1

    print(f"Linhas para traduzir: {len(tarefas)}")
    
    # 2. Tradução Neural (Annie)
    print("Carregando Annie...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
        model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)
    except:
        print("Erro ao carregar Annie. Verifique a pasta.")
        return

    print("Traduzindo...")
    for i, item in enumerate(tarefas):
        original = item["original"]
        if not precisa_traduzir(original):
            item["pt"] = original
        else:
            inputs = tokenizer(">>pt<< " + original, return_tensors="pt", padding=True)
            out = model.generate(**inputs, max_length=128, num_beams=4)
            item["pt"] = tokenizer.decode(out[0], skip_special_tokens=True)
        
        print(f"\rL{item['line_index']}: {item['pt'][:30]}... [Visuais: {len(item['visual_context'])}]", end="")

    # Salva para a Etapa 3 (que agora terá os dados visuais!)
    with open(ARQUIVO_TEMP, "w", encoding="utf-8") as f:
        json.dump(tarefas, f, indent=4)
    
    print("\nEtapa 1 Concluída. Dados visuais capturados.")

if __name__ == "__main__":
    main()
