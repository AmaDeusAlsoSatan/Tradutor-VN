import pandas as pd
df = pd.read_csv('Map002_Refinado.csv', encoding='utf-8')

print("Amostra aleatória de linhas (Best translation):\n")
for idx in [5, 10, 20, 30, 50, 75, 100, 150, 200, 250, 300]:
    if idx < len(df):
        orig = df.iloc[idx]['Original Text']
        best = df.iloc[idx]['Best translation']
        venc = df.iloc[idx]['Vencedor']
        print(f"[{idx}] Vencedor: {venc}")
        print(f"     EN: {str(orig)[:60]}...")
        print(f"     BEST: {str(best)[:90]}...")
        print()
