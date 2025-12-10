#!/usr/bin/env python3
"""
GERENCIADOR DO SNOWBALL DATASET
================================

Utilitário para:
1. Validar e limpar o dataset_snowball.json
2. Mesclar múltiplos datasets snowball (de várias Arenas)
3. Preparar dados para retreino com treinador_nmt.py
4. Gerar relatórios de qualidade

Uso:
    python snowball_manager.py --action validate --file dataset_snowball.json
    python snowball_manager.py --action merge --files file1.json file2.json --output merged.json
    python snowball_manager.py --action stats --file dataset_snowball.json
"""

import json
import argparse
from pathlib import Path
from collections import Counter
import sys


def validar_dataset(caminho_arquivo):
    """
    Valida estrutura do Snowball Dataset.
    
    Cada entrada deve ter:
    {
        "en": "English text",
        "pt": "Portuguese translation",
        "origem": "Snowball_Google",
        "score": 0.75
    }
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except FileNotFoundError:
        print(f"✗ Arquivo não encontrado: {caminho_arquivo}")
        return False
    except json.JSONDecodeError:
        print(f"✗ Arquivo JSON inválido: {caminho_arquivo}")
        return False
    
    if not isinstance(dados, list):
        print(f"✗ Root deve ser uma lista, não {type(dados).__name__}")
        return False
    
    print(f"\nValidando {caminho_arquivo}...")
    print(f"Total de pares: {len(dados)}")
    
    erros = []
    avisos = []
    campos_obrigatorios = {'en', 'pt', 'origem'}
    
    for idx, item in enumerate(dados):
        if not isinstance(item, dict):
            erros.append(f"  Linha {idx}: esperado dict, recebido {type(item).__name__}")
            continue
        
        # Verifica campos obrigatórios
        campos_faltantes = campos_obrigatorios - set(item.keys())
        if campos_faltantes:
            erros.append(f"  Linha {idx}: campos faltantes {campos_faltantes}")
            continue
        
        # Valida conteúdo
        en = item.get('en', '').strip()
        pt = item.get('pt', '').strip()
        
        if not en or len(en) < 2:
            erros.append(f"  Linha {idx}: 'en' vazio ou muito curto")
        if not pt or len(pt) < 2:
            erros.append(f"  Linha {idx}: 'pt' vazio ou muito curto")
        
        # Avisa sobre scores baixos (se presentes)
        if 'score' in item:
            score = item['score']
            if isinstance(score, (int, float)) and score < 0.55:
                avisos.append(f"  Linha {idx}: score baixo ({score:.2f})")
    
    # Relatório
    if erros:
        print(f"\n✗ Encontrados {len(erros)} erros:")
        for erro in erros[:10]:  # Mostra primeiros 10
            print(erro)
        if len(erros) > 10:
            print(f"  ... e {len(erros) - 10} mais")
        return False
    else:
        print(f"✓ Estrutura JSON válida")
    
    if avisos:
        print(f"\n⚠ {len(avisos)} avisos (scores baixos):")
        for aviso in avisos[:5]:
            print(aviso)
    
    return True


def limpar_dataset(caminho_entrada, caminho_saida, min_score=0.55):
    """
    Remove duplicatas e scores muito baixos.
    """
    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"✗ Erro ao ler: {e}")
        return False
    
    print(f"\nLimpando dataset...")
    print(f"Entrada: {len(dados)} pares")
    
    # Remove duplicatas (por par en->pt)
    vistos = set()
    limpos = []
    duplicatas = 0
    
    for item in dados:
        en = item.get('en', '').strip()
        pt = item.get('pt', '').strip()
        score = item.get('score', 0.75)
        
        # Pula scores muito baixos
        if score < min_score:
            continue
        
        chave = (en, pt)
        if chave in vistos:
            duplicatas += 1
        else:
            vistos.add(chave)
            limpos.append(item)
    
    print(f"Saída: {len(limpos)} pares (removidas {duplicatas} duplicatas)")
    
    try:
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(limpos, f, indent=4, ensure_ascii=False)
        print(f"✓ Salvo em: {caminho_saida}")
        return True
    except Exception as e:
        print(f"✗ Erro ao salvar: {e}")
        return False


def mesclar_datasets(*caminhos_arquivo, output=None):
    """
    Mescla múltiplos Snowball Datasets em um único.
    """
    todos_dados = []
    total_original = 0
    
    print(f"\nMesclando {len(caminhos_arquivo)} datasets...")
    
    for caminho in caminhos_arquivo:
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            print(f"  ✓ {Path(caminho).name}: {len(dados)} pares")
            todos_dados.extend(dados)
            total_original += len(dados)
        except Exception as e:
            print(f"  ✗ Erro ao ler {caminho}: {e}")
            return False
    
    # Remove duplicatas no merged
    vistos = set()
    unicos = []
    duplicatas = 0
    
    for item in todos_dados:
        en = item.get('en', '').strip()
        pt = item.get('pt', '').strip()
        chave = (en, pt)
        
        if chave in vistos:
            duplicatas += 1
        else:
            vistos.add(chave)
            unicos.append(item)
    
    print(f"Total após mesclagem: {len(unicos)} pares")
    print(f"Duplicatas removidas: {duplicatas}")
    
    if output:
        try:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(unicos, f, indent=4, ensure_ascii=False)
            print(f"✓ Salvo em: {output}")
            return True
        except Exception as e:
            print(f"✗ Erro ao salvar: {e}")
            return False
    
    return True


def gerar_stats(caminho_arquivo):
    """
    Gera estatísticas do dataset.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"✗ Erro ao ler: {e}")
        return
    
    print(f"\n{'='*60}")
    print(f"ESTATÍSTICAS: {Path(caminho_arquivo).name}")
    print(f"{'='*60}")
    
    # Contagem geral
    print(f"\nTamanho do dataset: {len(dados)} pares")
    
    # Análise de comprimento
    comprimentos_en = [len(item.get('en', '').split()) for item in dados]
    comprimentos_pt = [len(item.get('pt', '').split()) for item in dados]
    
    print(f"\nComprimento dos textos (palavras):")
    print(f"  Inglês:  min={min(comprimentos_en) if comprimentos_en else 0}, "
          f"max={max(comprimentos_en) if comprimentos_en else 0}, "
          f"média={sum(comprimentos_en)/len(comprimentos_en) if comprimentos_en else 0:.1f}")
    print(f"  Português: min={min(comprimentos_pt) if comprimentos_pt else 0}, "
          f"max={max(comprimentos_pt) if comprimentos_pt else 0}, "
          f"média={sum(comprimentos_pt)/len(comprimentos_pt) if comprimentos_pt else 0:.1f}")
    
    # Análise de origem
    origens = Counter(item.get('origem', 'desconhecida') for item in dados)
    print(f"\nOrigens dos pares:")
    for origem, count in origens.most_common():
        print(f"  {origem}: {count}")
    
    # Análise de scores (se presentes)
    scores = [item.get('score', 0.75) for item in dados if 'score' in item]
    if scores:
        print(f"\nScores de qualidade (TransQuest):")
        print(f"  Mínimo: {min(scores):.3f}")
        print(f"  Máximo: {max(scores):.3f}")
        print(f"  Média:  {sum(scores)/len(scores):.3f}")
        
        # Distribuição
        ranges = [(0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.0)]
        print(f"\n  Distribuição por faixa:")
        for min_s, max_s in ranges:
            count = sum(1 for s in scores if min_s <= s < max_s)
            pct = count / len(scores) * 100
            print(f"    {min_s:.1f}-{max_s:.1f}: {count} ({pct:.1f}%)")
    
    # Exemplos
    print(f"\nExemplos aleatórios (primeiros 3):")
    for idx, item in enumerate(dados[:3]):
        print(f"\n  [{idx+1}] EN: {item.get('en', '')[:60]}...")
        print(f"      PT: {item.get('pt', '')[:60]}...")
        if 'score' in item:
            print(f"      Score: {item['score']:.3f}")
    
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Gerenciador do Snowball Dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python snowball_manager.py --action validate --file dataset_snowball.json
  python snowball_manager.py --action clean --file dataset_snowball.json --output cleaned.json
  python snowball_manager.py --action merge --files file1.json file2.json --output merged.json
  python snowball_manager.py --action stats --file dataset_snowball.json
        """
    )
    
    parser.add_argument('--action', required=True, 
                       choices=['validate', 'clean', 'merge', 'stats'],
                       help='Ação a executar')
    parser.add_argument('--file', help='Arquivo principal')
    parser.add_argument('--files', nargs='+', help='Múltiplos arquivos (para merge)')
    parser.add_argument('--output', help='Arquivo de saída')
    parser.add_argument('--min-score', type=float, default=0.55,
                       help='Score mínimo para limpeza (padrão: 0.55)')
    
    args = parser.parse_args()
    
    # Valida argumentos
    if args.action == 'validate' and not args.file:
        print("✗ --action validate requer --file")
        sys.exit(1)
    elif args.action == 'clean' and not args.file:
        print("✗ --action clean requer --file")
        sys.exit(1)
    elif args.action == 'merge' and not args.files:
        print("✗ --action merge requer --files")
        sys.exit(1)
    elif args.action == 'stats' and not args.file:
        print("✗ --action stats requer --file")
        sys.exit(1)
    
    # Executa ação
    if args.action == 'validate':
        sucesso = validar_dataset(args.file)
        sys.exit(0 if sucesso else 1)
    
    elif args.action == 'clean':
        output = args.output or args.file.replace('.json', '_cleaned.json')
        sucesso = limpar_dataset(args.file, output, args.min_score)
        sys.exit(0 if sucesso else 1)
    
    elif args.action == 'merge':
        output = args.output or 'merged_snowball.json'
        sucesso = mesclar_datasets(*args.files, output=output)
        sys.exit(0 if sucesso else 1)
    
    elif args.action == 'stats':
        gerar_stats(args.file)
        sys.exit(0)


if __name__ == "__main__":
    main()
