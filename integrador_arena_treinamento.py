#!/usr/bin/env python3
"""
INTEGRADOR: Arena → Treinador NMT
==================================

Script que facilita a integração entre a Arena e o treinador_nmt.py.

Automatiza:
1. Validação do dataset_snowball.json
2. Conversão para formato esperado pelo treinador_nmt.py
3. Execução automática do treinamento
4. Relatório pós-treinamento

Uso:
    python integrador_arena_treinamento.py --dataset dataset_snowball.json
    python integrador_arena_treinamento.py --dataset dataset_snowball.json --epochs 3 --auto
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path


def validar_snowball_json(caminho):
    """Valida se o Snowball JSON está bem formado"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except FileNotFoundError:
        print(f"✗ Arquivo não encontrado: {caminho}")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ JSON inválido: {e}")
        return False
    
    if not isinstance(dados, list):
        print(f"✗ Root deve ser uma lista")
        return False
    
    if len(dados) == 0:
        print(f"✗ Dataset vazio")
        return False
    
    # Valida primeiro item
    first = dados[0]
    if not isinstance(first, dict):
        print(f"✗ Itens devem ser dicts")
        return False
    
    if 'en' not in first or 'pt' not in first:
        print(f"✗ Itens devem ter campos 'en' e 'pt'")
        return False
    
    print(f"✓ Dataset válido: {len(dados)} pares")
    return True


def converter_para_treinamento(caminho_entrada, caminho_saida=None):
    """
    Converte dataset_snowball.json para formato de treinamento.
    
    Formato entrada:
    [{"en": "...", "pt": "...", "score": 0.75, ...}]
    
    Formato saída (compatível com treinador_nmt.py):
    {"en": ["...", "..."], "pt": ["...", "..."], ...}
    """
    if caminho_saida is None:
        caminho_saida = caminho_entrada.replace('.json', '_treino.json')
    
    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"✗ Erro ao ler: {e}")
        return False
    
    # Converte para formato de listas
    en_lista = []
    pt_lista = []
    scores = []
    
    for item in dados:
        en = item.get('en', '').strip()
        pt = item.get('pt', '').strip()
        score = item.get('score', 0.75)
        
        if en and pt:  # Valida
            en_lista.append(en)
            pt_lista.append(pt)
            scores.append(score)
    
    # Cria estrutura de saída
    output = {
        "en": en_lista,
        "pt": pt_lista,
        "origem": [item.get('origem', 'Snowball') for item in dados[:len(en_lista)]],
        "scores": scores,
        "total": len(en_lista)
    }
    
    try:
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
        print(f"✓ Convertido para: {caminho_saida}")
        print(f"  Total de pares: {len(en_lista)}")
        return caminho_saida
    except Exception as e:
        print(f"✗ Erro ao salvar: {e}")
        return False


def gerar_relatorio(caminho_dataset):
    """Gera relatório do dataset antes de treinar"""
    try:
        with open(caminho_dataset, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except:
        return
    
    if not isinstance(dados, list) or len(dados) == 0:
        return
    
    print(f"\n{'='*60}")
    print("ANÁLISE DO DATASET ANTES DO TREINAMENTO")
    print(f"{'='*60}")
    
    # Comprimento
    en_words = [len(item.get('en', '').split()) for item in dados]
    pt_words = [len(item.get('pt', '').split()) for item in dados]
    
    print(f"\nComprimento médio:")
    print(f"  EN: {sum(en_words)/len(en_words):.1f} palavras")
    print(f"  PT: {sum(pt_words)/len(pt_words):.1f} palavras")
    
    # Scores
    scores = [item.get('score', 0.75) for item in dados if 'score' in item]
    if scores:
        print(f"\nQualidade média: {sum(scores)/len(scores):.3f}")
    
    # Origens
    from collections import Counter
    origens = Counter(item.get('origem', 'desconhecida') for item in dados)
    print(f"\nOrigens:")
    for origem, count in origens.most_common():
        print(f"  {origem}: {count}")
    
    print(f"\n{'='*60}\n")


def executar_treinamento(caminho_dataset, epochs=3, batch_size=16, auto=False):
    """Executa o treinador_nmt.py com o dataset Snowball"""
    
    # Verifica se treinador_nmt.py existe
    if not Path("treinador_nmt.py").exists():
        print("✗ treinador_nmt.py não encontrado na pasta atual")
        return False
    
    # Valida dataset
    if not validar_snowball_json(caminho_dataset):
        return False
    
    # Gera relatório
    gerar_relatorio(caminho_dataset)
    
    # Pergunta confirmação (se não --auto)
    if not auto:
        print(f"Pronto para treinar:")
        print(f"  Dataset: {caminho_dataset}")
        print(f"  Epochs: {epochs}")
        print(f"  Batch Size: {batch_size}")
        resposta = input("\nContinuar? [s/n] ").strip().lower()
        if resposta != 's':
            print("Cancelado.")
            return False
    
    # Executa treinador
    print(f"\n{'='*60}")
    print("INICIANDO TREINAMENTO")
    print(f"{'='*60}\n")
    
    cmd = [
        sys.executable,
        "treinador_nmt.py",
        "--dataset", caminho_dataset,
        "--epochs", str(epochs),
        "--batch-size", str(batch_size)
    ]
    
    try:
        resultado = subprocess.run(cmd, check=False)
        
        if resultado.returncode == 0:
            print(f"\n{'='*60}")
            print("✓ TREINAMENTO CONCLUÍDO COM SUCESSO")
            print(f"{'='*60}")
            print("\nPróximas etapas:")
            print("  1. Execute a Arena novamente com novos mapas")
            print("  2. Compare resultados com Arena anterior")
            print("  3. Observe melhoria em Annie (% de vitórias)")
            return True
        else:
            print(f"\n✗ Treinamento falhou com código: {resultado.returncode}")
            return False
    
    except Exception as e:
        print(f"✗ Erro ao executar treinador: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Integrador Arena ↔ Treinador NMT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Validar dataset
  python integrador_arena_treinamento.py --dataset dataset_snowball.json

  # Treinar com confirmação
  python integrador_arena_treinamento.py --dataset dataset_snowball.json --epochs 3

  # Treinar automaticamente (sem perguntas)
  python integrador_arena_treinamento.py --dataset dataset_snowball.json --epochs 3 --auto

  # Converter formato
  python integrador_arena_treinamento.py --dataset dataset_snowball.json --converter
        """
    )
    
    parser.add_argument('--dataset', required=True, help='Arquivo Snowball JSON')
    parser.add_argument('--epochs', type=int, default=3, help='Número de epochs (padrão: 3)')
    parser.add_argument('--batch-size', type=int, default=16, help='Tamanho de batch (padrão: 16)')
    parser.add_argument('--auto', action='store_true', help='Executar sem confirmação')
    parser.add_argument('--converter', action='store_true', help='Só converter formato, sem treinar')
    
    args = parser.parse_args()
    
    # Validar dataset
    print(f"\n{'='*60}")
    print("INTEGRADOR: Arena → Treinador NMT")
    print(f"{'='*60}\n")
    
    if not validar_snowball_json(args.dataset):
        sys.exit(1)
    
    # Se só converter
    if args.converter:
        converter_para_treinamento(args.dataset)
        sys.exit(0)
    
    # Converter para formato de treinamento
    dataset_treino = converter_para_treinamento(args.dataset)
    if not dataset_treino:
        sys.exit(1)
    
    # Executar treinamento
    sucesso = executar_treinamento(
        args.dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        auto=args.auto
    )
    
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Operação interrompida pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
