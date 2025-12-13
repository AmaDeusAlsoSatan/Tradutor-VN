TITAN - Arena de Tradução (Manual/Semi-automática)

Resumo
------
TITAN é uma interface gráfica para comparar traduções geradas por Annie (modelo local) e serviços web, proteger tags, revisar contexto e salvar decisões aprovadas em `dataset_snowball.json` para retreino.

Como usar
---------
1. Ative seu ambiente virtual:

```powershell
& ./venv_ia/Scripts/Activate.ps1
```

2. Instale dependências mínimas (recomendado):

```powershell
pip install customtkinter pandas openpyxl deep-translator g4f transformers torch
```

3. Rode o TITAN:

```powershell
python titan_arena.py
```

Funcionalidades
---------------
- Proteção de tags (mascara/desmascara) para evitar tradução de códigos.
- Carregamento de `Map002.csv`/XLSX para exibir contexto.
- Arena: Annie (local), Google (via `deep-translator`) e GPT (via `g4f`).
- Juiz: TransQuest quando disponível; caso contrário, heurística usada.
- Salva candidatos e decisão final em `dataset_snowball.json`.
- Botão para rodar o `treinador_nmt.py` (retrain) diretamente da UI e ver log em tempo real.

Notas
-----
- Se não quiser usar serviços web, desinstale `g4f`/`deep-translator` e o TITAN continuará funcionando localmente com Annie.
- Para usar TransQuest é recomendável emparelhar `protobuf==3.20.3` se houver erros de carregamento.

Contribuições
-------------
Este é um MVP. Melhorias possíveis: adicionar DeepL, Claude, BLEU/TER scoring, fuzzy-matching para o contexto e undo/redo no histórico.
