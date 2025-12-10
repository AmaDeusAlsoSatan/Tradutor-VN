#!/usr/bin/env python3
"""
ARENA - Ciclo Virtuoso de Treinamento
======================================

Este script implementa o padrão "Arena" onde:
1. A Annie (modelo local) compete com traduções online (Google/Bing)
2. Um Juiz (TransQuest) avalia a qualidade de ambas
3. A tradução melhor é escolhida
4. Traduções online vencedoras alimentam o "Snowball Dataset" para retreino

ENTRADA: CSV exportado do Translator++ (Map002.xlsx - Worksheet.csv)
SAÍDA:   CSV atualizado (Map002_Refinado.csv) + Dataset de treino (dataset_snowball.json)

Baseado em: etapa_3_blindada.py + Otimização com Máscara de Tags
Autor: Seu Script de IA
Data: 2025-12-10
"""

import pandas as pd
import re
import os
import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForSequenceClassification

# --- CONFIGURAÇÕES ---
ARQUIVO_ENTRADA = "Map002.csv"                   # Exportado do Translator++
ARQUIVO_SAIDA = "Map002_Refinado.csv"            # Para importar de volta
CAMINHO_ANNIE = "./modelo_annie_v1"              # Sua IA (MarianMT fine-tuned)
CAMINHO_QE = "TransQuest/monotransquest-da-multilingual"  # Seu Juiz de Qualidade
ARQUIVO_TREINO_FUTURO = "dataset_snowball.json"  # Ouro para o futuro (retreino)

# Limiar de qualidade para salvar no Snowball
LIMIAR_QUALIDADE_SNOWBALL = 0.60


# --- 1. FUNÇÃO DE MÁSCARA (PROTEÇÃO DE TAGS) ---
# Baseado na teoria do PDF "Otimizando Tradução com IA Local"
def mascarar_tags(texto):
    """
    Substitui tags do RPG Maker/RenPy por tokens seguros (__TAG_N__)
    
    Captura:
    1. Códigos de controle: \\V[1], \\N[2], \\C[0], \\I[5]
    2. Tags de formatação: {i}, {/i}, {color}, {/color}
    3. Quebras de linha explícitas: \\n
    4. Outros comandos de escape
    
    Teoricamente, a IA NÃO alucinará sobre tags porque ela não as vê.
    """
    if not isinstance(texto, str):
        return texto, {}
    
    mapa_tags = {}
    contador = 0
    
    # Regex agressivo para capturar comandos de RPGs e VNs
    # Padrão: (barra invertida + letra + colchetes) OU (chaves + conteúdo)
    padrao = r'(\\[a-zA-Z]+\[.*?\]|\\[a-zA-Z]+|{[^}]*}|\\n)'
    
    def substituir(match):
        nonlocal contador
        token = f"__TAG_{contador}__"
        mapa_tags[token] = match.group(0)
        contador += 1
        return token

    texto_mascarado = re.sub(padrao, substituir, texto, flags=re.IGNORECASE)
    return texto_mascarado, mapa_tags


def desmascarar_tags(texto_traduzido, mapa_tags):
    """
    Restaura as tags originais no lugar dos tokens.
    
    Tolerante com espaçamento (ex: __ TAG_0 __ será restaurado para tag original)
    """
    if not isinstance(texto_traduzido, str):
        return str(texto_traduzido)
    
    for token, tag_original in mapa_tags.items():
        # Remove espaços ao redor do token para robustez
        padrao_flexivel = rf'\s*{re.escape(token)}\s*'
        texto_traduzido = re.sub(padrao_flexivel, tag_original, texto_traduzido, flags=re.IGNORECASE)
    
    return texto_traduzido


# --- 2. CARREGAR MODELOS ---
print("=" * 70)
print("ARENA - Ciclo Virtuoso de Treinamento")
print("=" * 70)
print("\n[1/3] Carregando Annie (MarianMT)...")

try:
    tokenizer_annie = AutoTokenizer.from_pretrained(CAMINHO_ANNIE)
    model_annie = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_ANNIE)
    print(f"✓ Annie carregada de: {CAMINHO_ANNIE}")
except Exception as e:
    print(f"✗ ERRO ao carregar Annie: {e}")
    exit(1)

print("[2/3] Carregando Juiz (TransQuest)...")
TEM_QE = False
try:
    tokenizer_qe = AutoTokenizer.from_pretrained(CAMINHO_QE)
    model_qe = AutoModelForSequenceClassification.from_pretrained(CAMINHO_QE)
    TEM_QE = True
    print(f"✓ Juiz (TransQuest) carregado")
except Exception as e:
    print(f"⚠ AVISO: TransQuest não disponível ({e})")
    print(f"  Usando heurística simples (comprimento + keywords).")


def traduzir_annie(texto):
    """
    Traduz texto com Annie, protegendo tags.
    
    Fluxo:
    1. Mascara tags (ex: "Hello {i}World{/i}" -> "Hello __TAG_0__World__TAG_1__")
    2. Passa para Annie (modelo só vê o texto seguro)
    3. Desmascara (restaura tags na saída)
    """
    if not texto or len(texto.strip()) < 2:
        return ""
    
    texto_seguro, mapa = mascarar_tags(texto)
    
    try:
        inputs = tokenizer_annie(texto_seguro, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model_annie.generate(**inputs, max_length=512, num_beams=4)
        traducao_raw = tokenizer_annie.decode(outputs[0], skip_special_tokens=True)
        return desmascarar_tags(traducao_raw, mapa)
    except Exception as e:
        print(f"  ✗ Erro ao traduzir com Annie: {e}")
        return ""


def avaliar_qualidade(original, traducao):
    """
    Retorna score de qualidade 0.0 a 1.0.
    
    Se TransQuest estiver disponível: usa o modelo real
    Se não: usa heurística simples (comprimento + keywords)
    """
    if not original or not traducao:
        return 0.0
    
    if TEM_QE:
        try:
            # TransQuest espera formato: "source [SEP] target"
            entrada = f"{original} [SEP] {traducao}"
            inputs = tokenizer_qe(entrada, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                logits = model_qe(**inputs).logits
            
            # Normaliza a saída para 0.0-1.0
            # Se o modelo tem apenas 1 classe (default), usa o score diretamente
            if logits.shape[1] == 1:
                score = torch.sigmoid(logits[0][0]).item()
            else:
                score = torch.sigmoid(logits[0][1]).item()
            return score
        except Exception as e:
            # Fallback silencioso para heurística (sem print de erro)
            return _heuristica_qualidade(original, traducao)
    else:
        return _heuristica_qualidade(original, traducao)


def _heuristica_qualidade(original, traducao):
    """
    Heurística simples: baseada em comprimento e preservação de estrutura.
    
    Critérios:
    - Comprimento similar (±30%)
    - Preservação de pontuação
    - Sem tags aleatórias
    """
    if not traducao:
        return 0.0
    
    # Razão de comprimento
    len_orig = len(original.split())
    len_trad = len(traducao.split())
    razao = len_trad / len_orig if len_orig > 0 else 1.0
    
    # Score baseado em razão (ideal 0.8-1.2)
    if 0.7 <= razao <= 1.3:
        score = 0.7
    else:
        score = 0.4
    
    # Bônus por preservação de pontuação
    pontos_orig = sum(1 for c in original if c in '.,!?;:"')
    pontos_trad = sum(1 for c in traducao if c in '.,!?;:"')
    if pontos_orig > 0 and pontos_trad >= pontos_orig:
        score += 0.2
    
    # Penalidade por tags anômalas (ex: __TAG aparece sem ser fechado)
    if '__TAG_' in traducao and traducao.count('__TAG_') > traducao.count('__'):
        score -= 0.3
    
    return min(max(score, 0.0), 1.0)


def is_system_command(text: str) -> bool:
    """
    Detecta se a linha é um comando/sinalização do engine (nomes de arquivos, camadas, paths de áudio, etc.)
    Evita que comandos como 'LAYER_S 0 BedroomBottom' sejam traduzidos.
    """
    if not text:
        return False
    t = text.strip()
    # Prefixos comuns que não devem ser traduzidos
    prefixes = ('LAYER_', 'LAYER', 'Audio/', 'Audio\\', 'img/', 'Image/', 'Sprites/', 'Sprite/', 'Texture', 'ATTACH', 'PATH ')
    for p in prefixes:
        if t.startswith(p):
            return True

    # Arquivos com extensões (png, jpg, wav, ogg, mp3, json)
    if re.search(r"\.(png|jpg|jpeg|ogg|wav|mp3|json|xml|ini)\b", t, flags=re.IGNORECASE):
        return True

    # Sequências tipo "LAYER_S 0 BedroomBottom" — contém underscore + número + palavra composta
    if re.match(r'^[A-Z0-9_]+\s+\d', t):
        return True

    # Linhas muito curtas e totalmente maiúsculas podem ser comandos (ex: "OK", "END") — ignorar traduzir
    if len(t) <= 6 and t.upper() == t:
        return True

    return False


def is_probably_spanish(text: str) -> bool:
    """
    Detecta se a tradução parece estar em Espanhol (sinais de alerta).
    Usado para evitar salvar pares contaminados no Snowball.
    
    Pistas de espanhol: usted, vosotros, porque (sem acento), ¿, ¡, dormitorio, etc.
    """
    if not text:
        return False
    
    t = text.lower()
    spanish_markers = [
        r'\busted\b',       # "usted" (você em espanhol formal)
        r'\busted\s',       # "usted " (com espaço)
        r'\bvos\b',         # "vos" (você em algumas variantes)
        r'\bvosotros\b',    # "vosotros" (vós)
        r'\bustedes\b',     # "ustedes" (vocês)
        r'(?<!a)porque\b',  # "porque" sem tilde (em português é com tilde: porquê)
        r'[¿¡]',            # Pontuação espanhola invertida
        r'\bdormitorio\b',  # "dormitório" em espanhol
        r'\btiene\b',       # "tiene" (tem em espanhol)
        r'\btenía\b',       # "tenía" (tinha em espanhol)
        r'\bpero\b',        # "pero" (mas em espanhol)
        r'\bqué\b',         # "qué" (com tilde)
    ]
    
    for marker in spanish_markers:
        if re.search(marker, t, flags=re.IGNORECASE):
            return True
    
    return False


def detect_spanish_leak(text: str) -> bool:
    """
    Detecta vazamento de espanhol típico do MarianMT (opus-mt-en-ROMANCE).
    
    Identifica palavras muito comuns em espanhol que raramente aparecem em português
    ou têm uso bem diferente. Usado para desclassificar traduções da Annie que caíram
    na pegadilha do espanhol.
    """
    if not isinstance(text, str):
        return False
    
    text_lower = text.lower()
    
    # Palavras e padrões que são muito mais comuns/significativos em espanhol
    # do que em português, ou que indicam vazamento de código espanhol
    spanish_triggers = [
        (' usted', 'você formal (ES)'),
        (' y ', 'e (português usa "e", mas padrão é diferente)'),
        (' el ', 'o/o (artigo ES, raro em PT neste contexto)'),
        (' la ', 'a (artigo ES, em PT é mais contextual)'),
        (' los ', 'os (artigo ES, padrão ES típico)'),
        (' las ', 'as (artigo ES, padrão ES típico)'),
        (' pero ', 'mas/porém (mas típico de ES)'),
        (' habita', 'habita (ES, PT usa "mora")'),
        (' calle ', 'rua (calle é ES, PT usa rua)'),
        (' tengo ', 'tenho (forma ES primeira pessoa)'),
        (' tienes ', 'tens (forma ES segunda pessoa)'),
        (' eres ', 'és (forma ES de ser)'),
        (' estoy ', 'estou (menos comum em PT coloquial)'),
        (' hacia ', 'para (hacia é ES clássico)'),
        (' nada más', 'nada mais (nada más é padrão ES)'),
        (' entonces ', 'então (muito mais comum em ES)'),
    ]
    
    leak_indicators = []
    for trigger, label in spanish_triggers:
        if trigger in text_lower:
            leak_indicators.append(label)
    
    if leak_indicators:
        return True
    
    return False



# --- 3. A ARENA (LOOP PRINCIPAL) ---
def main():
    print("\n[3/3] Lendo dados do Translator++...")
    
    # Verifica se arquivo existe
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"✗ ERRO: Arquivo '{ARQUIVO_ENTRADA}' não encontrado!")
        print(f"  Exporte o mapa do Translator++ para CSV primeiro.")
        exit(1)
    
    # Lê o CSV
    try:
        df = pd.read_csv(ARQUIVO_ENTRADA, encoding='utf-8')
    except Exception as e:
        print(f"✗ Erro ao ler CSV: {e}")
        print(f"  Verifique o encoding e formato do arquivo.")
        exit(1)
    
    # Verifica colunas esperadas
    colunas_esperadas = ['Original Text', 'Machine translation']
    colunas_faltantes = [col for col in colunas_esperadas if col not in df.columns]
    if colunas_faltantes:
        print(f"✗ ERRO: Colunas não encontradas: {colunas_faltantes}")
        print(f"  Colunas disponíveis: {list(df.columns)}")
        exit(1)
    
    # Adiciona colunas de saída se não existirem
    # Garantir colunas de saída e tipo object (string) para evitar warns de dtype
    if 'Better translation' not in df.columns:
        df['Better translation'] = pd.Series(dtype=object)
    else:
        df['Better translation'] = df['Better translation'].astype(object)
    
    if 'Best translation' not in df.columns:
        df['Best translation'] = pd.Series(dtype=object)
    else:
        df['Best translation'] = df['Best translation'].astype(object)
    
    if 'Vencedor' not in df.columns:
        df['Vencedor'] = pd.Series(dtype=object)
    else:
        df['Vencedor'] = df['Vencedor'].astype(object)
    
    if 'Score Annie' not in df.columns:
        df['Score Annie'] = 0.0
    if 'Score Online' not in df.columns:
        df['Score Online'] = 0.0
    
    novos_treinos = []
    statisticas = {
        'total': 0,
        'annie_venceu': 0,
        'online_venceu': 0,
        'snowball_salvos': 0,
        'linhas_vazias': 0
    }
    
    print(f"\n{'='*70}")
    print(f"Iniciando Arena com {len(df)} linhas...")
    print(f"{'='*70}\n")
    
    for index, row in df.iterrows():
        original = str(row['Original Text']).strip() if pd.notna(row['Original Text']) else ""
        rival_online = str(row['Machine translation']).strip() if pd.notna(row['Machine translation']) else ""
        
        # Pula linhas vazias
        if not original or len(original) < 2:
            statisticas['linhas_vazias'] += 1
            continue
        
        statisticas['total'] += 1
        
        # Mostra progresso
        if statisticas['total'] % 10 == 0:
            print(f"[{statisticas['total']:4d}] Processando...", end='\r')
        
        # 1. Proteções para comandos/sistemas: não traduzir nomes de arquivos/paths
        if is_system_command(original):
            annie_traducao = original
            score_annie = 1.0
            score_rival = 0.0
            melhor_traducao = original
            origem_vencedora = "Annie (Protegido)"
            statisticas['annie_venceu'] += 1
            # Preenche colunas e pula o fluxo normal
            df.at[index, 'Better translation'] = annie_traducao
            df.at[index, 'Best translation'] = melhor_traducao
            df.at[index, 'Vencedor'] = origem_vencedora
            df.at[index, 'Score Annie'] = round(score_annie, 3)
            df.at[index, 'Score Online'] = round(score_rival, 3)
            continue

        # 2. Annie entra no ringue
        annie_traducao = traduzir_annie(original)
        
        # 2.5. Checagem "Anti-Despacito" — Annie caiu na pegadilha do espanhol?
        if annie_traducao and detect_spanish_leak(annie_traducao):
            print(f"\n  🚨 Annie falou espanhol na linha {index}: '{annie_traducao[:60]}...'")
            annie_traducao = ""  # Anula a tradução da Annie
            score_annie = 0.0    # Penalidade máxima

        # 3. O Juiz decide
        score_annie = avaliar_qualidade(original, annie_traducao) if annie_traducao else 0.0
        score_rival = avaliar_qualidade(original, rival_online) if rival_online else 0.0
        
        melhor_traducao = ""
        origem_vencedora = ""
        
        # 3. Lógica de Decisão
        if not annie_traducao:
            # Annie falhou, rival ganha por padrão
            melhor_traducao = rival_online
            origem_vencedora = "Online (Annie falhou)"
            statisticas['online_venceu'] += 1
        elif not rival_online:
            # Só temos Annie
            melhor_traducao = annie_traducao
            origem_vencedora = "Annie (Rival vazio)"
            statisticas['annie_venceu'] += 1
        elif score_annie >= score_rival:
            # Annie venceu ou empatou
            melhor_traducao = annie_traducao
            origem_vencedora = "Annie"
            statisticas['annie_venceu'] += 1
        else:
            # Rival venceu
            melhor_traducao = rival_online
            origem_vencedora = "Online"
            statisticas['online_venceu'] += 1
            
            # --- CICLO VIRTUOSO (SNOWBALL) ---
            # Se a tradução online for realmente boa E estiver em português, salvamos para retreino
            if score_rival > LIMIAR_QUALIDADE_SNOWBALL and not is_probably_spanish(rival_online):
                novos_treinos.append({
                    "en": original,
                    "pt": rival_online,
                    "origem": "Snowball_Google",
                    "score": float(score_rival)
                })
                statisticas['snowball_salvos'] += 1
        
        # 4. Preenche as colunas para re-importar no Translator++
        df.at[index, 'Better translation'] = annie_traducao
        df.at[index, 'Best translation'] = melhor_traducao
        df.at[index, 'Vencedor'] = origem_vencedora
        df.at[index, 'Score Annie'] = round(score_annie, 3)
        df.at[index, 'Score Online'] = round(score_rival, 3)
        
        # Debug verbose (descomente para troubleshoot)
        # print(f"L{index}: Annie({score_annie:.2f}) vs Online({score_rival:.2f}) -> {origem_vencedora}")
    
    # 5. Salva resultados
    print(f"\n{'='*70}")
    print("Salvando resultados...")
    
    try:
        df.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
        print(f"✓ CSV atualizado: {ARQUIVO_SAIDA}")
    except Exception as e:
        print(f"✗ Erro ao salvar CSV: {e}")
    
    # 6. Salva dados para retreino (Snowball)
    if novos_treinos:
        try:
            with open(ARQUIVO_TREINO_FUTURO, 'w', encoding='utf-8') as f:
                json.dump(novos_treinos, f, indent=4, ensure_ascii=False)
            print(f"✓ Snowball Dataset: {ARQUIVO_TREINO_FUTURO} ({len(novos_treinos)} pares)")
        except Exception as e:
            print(f"✗ Erro ao salvar Snowball: {e}")
    else:
        print(f"⚠ Nenhum par salvo no Snowball (limite de qualidade: >{LIMIAR_QUALIDADE_SNOWBALL})")
    
    # 7. Relatório final
    print(f"\n{'='*70}")
    print("RELATÓRIO FINAL")
    print(f"{'='*70}")
    print(f"Total de linhas processadas:  {statisticas['total']}")
    print(f"Linhas vazias ignoradas:      {statisticas['linhas_vazias']}")
    print(f"Annie venceu:                 {statisticas['annie_venceu']} ({statisticas['annie_venceu']/max(statisticas['total'],1)*100:.1f}%)")
    print(f"Online venceu:                {statisticas['online_venceu']} ({statisticas['online_venceu']/max(statisticas['total'],1)*100:.1f}%)")
    print(f"Salvos no Snowball:           {statisticas['snowball_salvos']}")
    
    if novos_treinos:
        print(f"\n💡 Próximo passo: Retreinar Annie com o Snowball Dataset")
        print(f"   $ python treinador_nmt.py --dataset {ARQUIVO_TREINO_FUTURO} --epochs 3")
    else:
        print(f"\n⚠ Nenhum dado novo para retreino. Ajuste LIMIAR_QUALIDADE_SNOWBALL se necessário.")
    
    print(f"\n✓ Importe '{ARQUIVO_SAIDA}' no Translator++ para continuar a revisão manual.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Processo interrompido pelo usuário.")
        exit(0)
    except Exception as e:
        print(f"\n✗ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
