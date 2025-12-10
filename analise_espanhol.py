import pandas as pd
import re

df = pd.read_csv('Map002_Refinado.csv')
print(f"Total de linhas: {len(df)}")
print(f"\nExaminando coluna 'Best translation' (vencedora):")
print(f"Não vazia: {df['Best translation'].notna().sum()}")
print(f"Vazia/NaN: {df['Best translation'].isna().sum()}")

# Ver algumas linhas com "Best translation" preenchida
print("\nPrimeiras 10 'Best translation' (vencedoras):")
for i, val in enumerate(df['Best translation'].head(10), 1):
    if pd.notna(val) and val != "":
        print(f"{i}. {str(val)[:80]}")

# Função para detectar espanhol (mesma do script)
def detect_spanish_leak(text: str) -> bool:
    if not isinstance(text, str):
        return False
    text_lower = text.lower()
    spanish_triggers = [
        (' usted', 'você formal (ES)'),
        (' y ', 'e (artigo ES)'),
        (' el ', 'o/o (artigo ES)'),
        (' la ', 'a (artigo ES)'),
        (' los ', 'os (artigo ES)'),
        (' las ', 'as (artigo ES)'),
        (' pero ', 'mas/porém (mas ES)'),
        (' habita', 'habita (ES, PT usa mora)'),
        (' calle ', 'rua (calle ES)'),
        (' tengo ', 'tenho (ES primeira)'),
        (' tienes ', 'tens (ES segunda)'),
        (' eres ', 'és (ES ser)'),
        (' estoy ', 'estou (ES menos comum PT)'),
        (' hacia ', 'para (hacia ES)'),
        (' nada más', 'nada mais (ES)'),
        (' entonces ', 'então (ES)'),
    ]
    
    for trigger, label in spanish_triggers:
        if trigger in text_lower:
            return True
    return False

# Contar espanhol nas vencedoras
spanish_count = 0
spanish_examples = []

for idx, row in df.iterrows():
    best = str(row['Best translation']) if pd.notna(row['Best translation']) else ""
    if best and best != "nan" and detect_spanish_leak(best):
        spanish_count += 1
        if len(spanish_examples) < 10:
            spanish_examples.append((idx, best))

print(f"\n\n{'='*80}")
print(f"RESULTADO: {spanish_count} linhas vencedoras ('Best translation') ainda em ESPANHOL")
print(f"{'='*80}")

if spanish_examples:
    print("\nExemplos das primeiras 10 linhas em espanhol:")
    for idx, text in spanish_examples:
        print(f"\nLinha {idx}:")
        print(f"  {text[:100]}...")

# Análise: qual foi o vencedor nessas linhas?
print(f"\n\nAnálise: Quem ganhou essas {spanish_count} linhas em espanhol?")
vencedores_espanhol = {}
for idx, row in df.iterrows():
    best = str(row['Best translation']) if pd.notna(row['Best translation']) else ""
    if best and best != "nan" and detect_spanish_leak(best):
        vencedor = row['Vencedor']
        vencedores_espanhol[vencedor] = vencedores_espanhol.get(vencedor, 0) + 1

print(vencedores_espanhol)

print(f"\n\nCONCLUSÃO: {vencedores_espanhol.get('Online', 0)} linhas 'Online' em espanhol + {vencedores_espanhol.get('Annie', 0)} linhas 'Annie' em espanhol")
