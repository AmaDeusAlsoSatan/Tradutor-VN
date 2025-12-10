import json
with open('dataset_snowball.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total pares no Snowball: {len(data)}")
print(f"\nPrimeiros 5 pares salvos:")

for i, pair in enumerate(data[:5], 1):
    print(f"\n[{i}] EN: {pair['en'][:70]}...")
    print(f"     PT: {pair['pt'][:70]}...")
    print(f"     Score: {pair['score']:.3f}")
    
    # Checagem simples de espanhol
    pt_lower = pair['pt'].lower()
    spanish_markers = {
        'usted': 'você (ES)',
        'porque': 'porque (ES)',
        'dormitorio': 'dormitório (ES)',
        'tenía': 'tinha (ES)',
        'qué': 'qué (ES)',
        '¿': 'invertido (ES)',
        '¡': 'invertido (ES)',
    }
    
    flagged = []
    for marker, label in spanish_markers.items():
        if marker in pt_lower:
            flagged.append(label)
    
    if flagged:
        print(f"     ⚠️ MARCADORES: {', '.join(flagged)}")
    else:
        print(f"     ✅ Parece português")

print(f"\nDone. Verificar se é necessário reprocestar com melhor detecção.")
