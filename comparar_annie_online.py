import pandas as pd
df = pd.read_csv('Map002_Refinado.csv', encoding='utf-8')

print("Comparação ANNIE (Better) vs ONLINE (Best translation):\n")
print("="*100)

# Pegar algumas linhas onde Annie foi desclassificada por espanhol
desclassificados = df[df['Vencedor'].str.contains('Annie falhou', na=False)].head(10)

for idx, row in desclassificados.iterrows():
    print(f"\n[LINHA {idx}]")
    print(f"EN: {str(row['Original Text'])[:70]}...")
    print(f"ANNIE (Better translation): {str(row['Better translation'])[:80]}...")
    print(f"ONLINE (Best translation): {str(row['Best translation'])[:80]}...")
    print(f"Vencedor: {row['Vencedor']}")
    print("-" * 100)

print("\n\nRESUMO:")
print(f"Total de linhas: {len(df)}")
print(f"Annie vitórias: {(df['Vencedor'].str.contains('Annie', na=False) & ~df['Vencedor'].str.contains('falhou', na=False)).sum()}")
print(f"Online vitórias: {(df['Vencedor'] == 'Online').sum()}")
print(f"Annie falhou: {df['Vencedor'].str.contains('falhou', na=False).sum()}")
print(f"Annie protegido: {(df['Vencedor'] == 'Annie (Protegido)').sum()}")
