#!/usr/bin/env python3
"""
Corrige linhas com aspas duplas escapadas no script.rpy
Problema: "\\"Texto.\\"" deveria ser simplesmente "Texto."
"""

import re

arquivo = r"C:\Users\Defal\Documents\Projeto\Jogos\inversed-1.0-pc\game\tl\portuguese\script.rpy"

with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Padrão correto encontrado
original_count = len(re.findall(r'"\\"', conteudo))

# Substitui "\\...\\\"" por "..."
conteudo_corrigido = re.sub(r'"\\"([^"]*?)\\\"', r'"\1"', conteudo)

corrigidas = original_count - len(re.findall(r'"\\"', conteudo_corrigido))

with open(arquivo, 'w', encoding='utf-8') as f:
    f.write(conteudo_corrigido)

print(f"✅ Total de ocorrências corrigidas: {corrigidas}")
print(f"Padrão corrigido: \"\\\\\"...\\\\\" → \"...\"")
