import pandas as pd, re, os
fname = 'Map002.csv' if os.path.exists('Map002.csv') else ('Map002.xlsx - Worksheet.csv' if os.path.exists('Map002.xlsx - Worksheet.csv') else None)
if not fname:
    print('No CSV found')
    raise SystemExit(1)
print('Reading', fname)
df = pd.read_csv(fname) if fname.endswith('.csv') else pd.read_excel(fname)

# Find LAYER_ occurrences
layer_idx = df['Original Text'].astype(str).str.contains('LAYER_', na=False)
print('LAYER_ occurrences:', layer_idx.sum())
print('\nSample LAYER_ rows:')
print(df.loc[layer_idx].head(5)[['Original Text','Machine translation']].to_string())

# Find Machine translations with Spanish cues
spanish_cues = ['usted','vos','vosotros','ustedes','porque','¿','¡','dormitorio','usted','Usted','nunca','tiene','tenía']
mt = df['Machine translation'].astype(str)
pattern = '|'.join([re.escape(s) for s in spanish_cues])
mask_span = mt.str.lower().str.contains(pattern, na=False)
print('\nPossible Spanish machine translations (count):', mask_span.sum())
print(df.loc[mask_span].head(10)[['Original Text','Machine translation']].to_string())

# Write a CSV with flagged lines for review
flagged = df.loc[mask_span | layer_idx]
if not flagged.empty:
    flagged.to_csv('Map002_flagged_for_review.csv', index=False)
    print('\nWrote Map002_flagged_for_review.csv with', len(flagged), 'rows')
else:
    print('\nNo flagged rows found')
