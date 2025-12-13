**TITAN: Arena de Tradução**

O `titan_arena.py` é uma GUI semi-automática para comparar traduções (Annie local + serviços web) e gerar um dataset controlado (`dataset_snowball.json`) e um histórico (`historico_titan.json`).

Instalação (recomendada dentro do `venv_ia`):

```powershell
pip install -r requirements_arena.txt
# se quiser evitar baixar o juiz agora, instale pelo menos:
pip install customtkinter pandas openpyxl deep-translator
```

Como rodar:

- GUI (Windows PowerShell):

```powershell
& ./venv_ia/Scripts/Activate.ps1
python titan_arena.py
```

- Teste rápido (headless):

```powershell
& ./venv_ia/Scripts/Activate.ps1
python titan_arena.py --smoke
# ou
python tests/test_titan_smoke.py
```

Notas:
- Se quiser usar o Juiz (TransQuest), instale `protobuf==3.20.3` antes de carregar o juiz.
- O botão `Treinar Annie` chama `treinador_nmt.py --dataset dataset_snowball.json --epochs N` usando o Python do ambiente ativo.
- Todos os salvamentos são feitos em `dataset_snowball.json` (para treino) e `historico_titan.json` (registro completo com candidatos e scores).
