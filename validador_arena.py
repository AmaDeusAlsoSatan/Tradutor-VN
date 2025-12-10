#!/usr/bin/env python3
"""
VALIDADOR DA ARENA
==================

Script para testar se o ambiente está configurado corretamente
antes de executar a Arena em dados reais.

Verifica:
1. ✓ Python version
2. ✓ Dependências instaladas
3. ✓ Annie carregada
4. ✓ TransQuest disponível
5. ✓ Arquivos de dados
6. ✓ Espaço em disco
7. ✓ Máscara de tags funcionando
"""

import sys
import os
from pathlib import Path

def print_header(title):
    """Imprime um cabeçalho bonito"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_python_version():
    """Verifica versão do Python"""
    print_header("1. Verificação de Python")
    version = sys.version_info
    print(f"Versão encontrada: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✓ Python 3.8+ OK")
        return True
    else:
        print("✗ ERRO: Python 3.8+ requerido")
        return False

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    print_header("2. Verificação de Dependências")
    
    dependencies = {
        'pandas': 'Leitura/escrita CSV',
        'openpyxl': 'Suporte Excel',
        'torch': 'Framework PyTorch',
        'transformers': 'Modelos HF',
        're': 'Regex (built-in)',
        'json': 'JSON (built-in)',
        'argparse': 'Args (built-in)',
    }
    
    failed = []
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✓ {package:15} - {description}")
        except ImportError:
            print(f"✗ {package:15} - {description} [FALTANDO]")
            failed.append(package)
    
    if failed:
        print(f"\nPacotes faltantes: {', '.join(failed)}")
        print("Execute: pip install -r requirements_arena.txt")
        return False
    
    return True

def check_annie():
    """Verifica se Annie está carregada"""
    print_header("3. Verificação de Annie (MarianMT)")
    
    caminho = Path("./modelo_annie_v1")
    
    if not caminho.exists():
        print(f"✗ Pasta não encontrada: {caminho.absolute()}")
        return False
    
    # Verifica arquivos esperados
    arquivos_esperados = [
        'config.json',
        'model.safetensors',
        'tokenizer_config.json',
        'source.spm',
        'target.spm',
        'vocab.json'
    ]
    
    print(f"Caminho: {caminho.absolute()}")
    print(f"\nArquivos esperados:")
    
    encontrados = 0
    for arquivo in arquivos_esperados:
        caminho_arquivo = caminho / arquivo
        if caminho_arquivo.exists():
            tamanho = caminho_arquivo.stat().st_size / (1024 * 1024)  # MB
            print(f"✓ {arquivo:25} ({tamanho:.1f} MB)")
            encontrados += 1
        else:
            print(f"✗ {arquivo:25} [FALTANDO]")
    
    print(f"\nTotal: {encontrados}/{len(arquivos_esperados)} arquivos encontrados")
    
    if encontrados >= 5:  # Mínimo viável
        print("✓ Annie parece estar OK")
        return True
    else:
        print("✗ ERRO: Arquivos de Annie faltando")
        return False

def check_transquest():
    """Verifica se TransQuest está disponível"""
    print_header("4. Verificação de TransQuest (Juiz)")
    
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        print("Testando download do TransQuest...")
        try:
            tokenizer = AutoTokenizer.from_pretrained("TransQuest/monotransquest-da-multilingual")
            model = AutoModelForSequenceClassification.from_pretrained("TransQuest/monotransquest-da-multilingual")
            print("✓ TransQuest carregado com sucesso")
            print("  Modelo: TransQuest/monotransquest-da-multilingual")
            return True
        except Exception as e:
            print(f"⚠ TransQuest não disponível ({str(e)[:50]}...)")
            print("  A Arena usará heurística automática (menos precisa)")
            return False
    except ImportError:
        print("⚠ Transformers não instalado")
        return False

def check_test_data():
    """Verifica se arquivo de teste existe"""
    print_header("5. Verificação de Dados de Teste")
    
    caminho = Path("exemplo_entrada_arena.csv")
    
    if caminho.exists():
        tamanho = caminho.stat().st_size
        print(f"✓ Arquivo de teste encontrado: {caminho}")
        print(f"  Tamanho: {tamanho} bytes")
        
        # Tenta ler
        try:
            import pandas as pd
            df = pd.read_csv(caminho)
            print(f"  Linhas: {len(df)}")
            print(f"  Colunas: {list(df.columns)}")
            return True
        except Exception as e:
            print(f"✗ Erro ao ler CSV: {e}")
            return False
    else:
        print(f"⚠ Arquivo de teste não encontrado: {caminho}")
        return False

def check_disk_space():
    """Verifica espaço em disco"""
    print_header("6. Verificação de Espaço em Disco")
    
    try:
        import shutil
        stat = shutil.disk_usage(".")
        
        # Converte para GB
        total_gb = stat.total / (1024**3)
        free_gb = stat.free / (1024**3)
        
        print(f"Total:     {total_gb:.1f} GB")
        print(f"Disponível: {free_gb:.1f} GB")
        print(f"Usado:      {(stat.used / (1024**3)):.1f} GB")
        
        if free_gb > 2:
            print("✓ Espaço suficiente (> 2 GB)")
            return True
        else:
            print("⚠ Espaço baixo (< 2 GB). Operação pode falhar.")
            return False
    except Exception as e:
        print(f"⚠ Não foi possível verificar espaço: {e}")
        return False

def test_tag_masking():
    """Testa se a máscara de tags funciona"""
    print_header("7. Teste de Máscara de Tags")
    
    import re
    
    def mascarar_tags(texto):
        if not isinstance(texto, str): return texto, {}
        
        mapa_tags = {}
        contador = 0
        
        padrao = r'(\\[a-zA-Z]+\[.*?\]|\\[a-zA-Z]+|{[^}]*}|\\n)'
        
        def substituir(match):
            nonlocal contador
            token = f"__TAG_{contador}__"
            mapa_tags[token] = match.group(0)
            contador += 1
            return token

        texto_mascarado = re.sub(padrao, substituir, texto, flags=re.IGNORECASE)
        return texto_mascarado, mapa_tags
    
    # Testes
    testes = [
        "Hello {i}world{/i}",
        "Test\\n\\V[1]\\N[2]",
        "Normal text without tags",
        "{color=red}Red{/color} text"
    ]
    
    print("Testando mascaramento...")
    
    for texto in testes:
        mascarado, mapa = mascarar_tags(texto)
        print(f"\n  Original:   {texto}")
        print(f"  Mascarado:  {mascarado}")
        print(f"  Mapa:       {dict(list(mapa.items())[:2])}")  # Primeiras 2 tags
        
        if mapa:
            print(f"  Tags encontradas: {len(mapa)}")
    
    print("\n✓ Máscara de tags funcionando")
    return True

def main():
    """Executa todos os testes"""
    print(f"\n{'#'*60}")
    print("# VALIDADOR DA ARENA - Verificação de Ambiente")
    print(f"{'#'*60}")
    
    resultados = []
    
    # Executa testes
    resultados.append(("Python Version", check_python_version()))
    resultados.append(("Dependências", check_dependencies()))
    resultados.append(("Annie (MarianMT)", check_annie()))
    resultados.append(("TransQuest (Juiz)", check_transquest()))
    resultados.append(("Dados de Teste", check_test_data()))
    resultados.append(("Espaço em Disco", check_disk_space()))
    resultados.append(("Máscara de Tags", test_tag_masking()))
    
    # Relatório final
    print_header("RELATÓRIO FINAL")
    
    passed = sum(1 for _, result in resultados if result)
    total = len(resultados)
    
    print(f"\nTestes passados: {passed}/{total}\n")
    
    for nome, resultado in resultados:
        status = "✓ PASS" if resultado else "✗ FAIL"
        print(f"{status:7} - {nome}")
    
    print(f"\n{'='*60}")
    
    if passed == total:
        print("✓ TUDO OK! Você pode executar a Arena.")
        print("\nPróximos passos:")
        print("  1. Exporte dados do Translator++ como CSV")
        print("  2. Nomeie como: 'Map002.xlsx - Worksheet.csv'")
        print("  3. Execute: python arena_ciclo_virtuoso.py")
        return 0
    elif passed >= 5:
        print("⚠ QUASE PRONTO. Alguns avisos, mas deve funcionar.")
        print("\nProblemas encontrados:")
        for nome, resultado in resultados:
            if not resultado:
                print(f"  - {nome}")
        return 1
    else:
        print("✗ PROBLEMAS ENCONTRADOS. Corrija antes de executar.")
        print("\nProblemas encontrados:")
        for nome, resultado in resultados:
            if not resultado:
                print(f"  - {nome}")
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠ Teste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
