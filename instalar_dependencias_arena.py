#!/usr/bin/env python3
"""
INSTALADOR DE DEPENDÊNCIAS PARA A ARENA
========================================

Este script instala todas as dependências necessárias para executar
a Arena e o Ciclo Virtuoso de Treinamento.
"""

import subprocess
import sys

def run_command(cmd, description=""):
    """Executa comando e relata resultado"""
    if description:
        print(f"\n{'='*60}")
        print(f"► {description}")
        print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao executar: {cmd}")
        return False


def main():
    print(f"\n{'='*60}")
    print("ARENA - Instalador de Dependências")
    print(f"{'='*60}")
    
    # Dependências principais
    packages = [
        ('pandas', 'Leitura/escrita de CSV e manipulação de dados'),
        ('openpyxl', 'Suporte para arquivos Excel (.xlsx)'),
        ('torch', 'Framework PyTorch (para transformers)'),
        ('transformers', 'Modelos de IA (Hugging Face)'),
        ('torchaudio', 'Utilitários de áudio (dependência do torch)'),
    ]
    
    print("\nInstalando pacotes necessários...")
    
    failed = []
    for package, description in packages:
        print(f"\n[{package}] {description}...", end=" ", flush=True)
        
        if run_command(f"{sys.executable} -m pip install {package}", ""):
            print("✓")
        else:
            print("✗")
            failed.append(package)
    
    # Relatório final
    print(f"\n{'='*60}")
    print("RELATÓRIO DE INSTALAÇÃO")
    print(f"{'='*60}")
    
    if not failed:
        print("\n✓ Todas as dependências instaladas com sucesso!")
        print("\nPróximos passos:")
        print("  1. Exporte seu mapa do Translator++ para CSV")
        print("  2. Nomeie o arquivo como: Map002.xlsx - Worksheet.csv")
        print("  3. Execute: python arena_ciclo_virtuoso.py")
        print("  4. Se novos dados forem gerados, retreine com:")
        print("     python treinador_nmt.py --dataset dataset_snowball.json --epochs 3")
        return 0
    else:
        print(f"\n✗ Falha ao instalar {len(failed)} pacote(s):")
        for pkg in failed:
            print(f"  - {pkg}")
        print("\nTente executar manualmente:")
        for pkg in failed:
            print(f"  pip install {pkg}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
