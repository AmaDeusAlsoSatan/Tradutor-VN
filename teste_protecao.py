import pandas as pd
import re
from pathlib import Path

# --- CONFIGURAÇÃO ---
# Tenta vários nomes possíveis que podem existir no seu workspace
CANDIDATOS = [
    "Map002.xlsx - Worksheet.csv",
    "Map002.csv",
    "Map002.xlsx",
]

ARQUIVO_CSV = None
for c in CANDIDATOS:
    if Path(c).exists():
        ARQUIVO_CSV = c
        break

# --- LÓGICA DE PROTEÇÃO (A mesma que usaremos na Arena) ---

def is_system_command(texto):
    if not isinstance(texto, str):
        return True  # Protege vazios/números
    texto = texto.strip()
    if texto == "":
        return True

    # Lista de prefixos proibidos (comandos do RPG Maker/RenPy)
    proibidos = [
        "LAYER_", "Audio/", "Image/", "Script/", 
        "Show Picture", "Play SE", "Play BGM",
        "BEAT", "---"
    ]

    # 1. Checa prefixos
    for p in proibidos:
        if texto.startswith(p):
            return True

    # 2. Checa se parece nome de arquivo (sem espaços e com extensão comum)
    # Ex: "background_room.png" ou "BedroomBottom.png"
    if re.match(r'^[\w\-]+\.(png|jpg|ogg|mp3|wav)$', texto, re.IGNORECASE):
        return True

    # 3. Se a linha contém muitos códigos/identificadores (como LAYER_S seguido de números), proteger
    if re.match(r'^[A-Z0-9_]+\s+[0-9]', texto):
        return True

    return False

# --- EXECUÇÃO DO TESTE ---
try:
    if ARQUIVO_CSV is None:
        raise FileNotFoundError(f"Nenhum dos arquivos esperados foi encontrado: {CANDIDATOS}")

    print(f"Lendo '{ARQUIVO_CSV}'...\n")

    # Tenta ler como CSV (se for .xlsx, pandas cuidará se engine apropriada existir)
    if ARQUIVO_CSV.lower().endswith('.xlsx'):
        df = pd.read_excel(ARQUIVO_CSV)
    else:
        df = pd.read_csv(ARQUIVO_CSV)

    print("--- RELATÓRIO DE PROTEÇÃO (Primeiras 30 linhas) ---")
    print(f"{'LINHA':<5} | {'STATUS':<12} | {'TEXTO ORIGINAL'}")
    print("-" * 100)

    for index, row in df.head(30).iterrows():
        original = row.get('Original Text') if 'Original Text' in df.columns else row.iloc[0]
        original = str(original) if not pd.isna(original) else ""
        protegido = is_system_command(original)

        status = "🛑 PROTEGIDO" if protegido else "✅ TRADUZIR"
        cor_texto = original[:80].replace('\n', ' ')

        print(f"{index:<5} | {status:<12} | {cor_texto}")

    print("\nTeste concluído. Se linhas como 'LAYER_S' aparecem como '🛑 PROTEGIDO', a proteção está funcionando.")

except FileNotFoundError as e:
    print(f"ERRO: {e}")
except Exception as e:
    print(f"ERRO GERAL: {e}")
