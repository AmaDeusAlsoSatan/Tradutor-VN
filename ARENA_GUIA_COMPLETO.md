# ARENA - Ciclo Virtuoso de Treinamento
## Documentação Completa

---

## 1. O que é a Arena?

A **Arena** é um sistema automático de tradução comparativa que:

1. **Lê** dados do Translator++ (arquivo CSV exportado)
2. **Executa** Annie (seu modelo MarianMT) contra traduções online (Google/Bing)
3. **Avalia** qualidade de ambas com TransQuest (juiz de qualidade)
4. **Escolhe** a tradução melhor
5. **Alimenta** o "Snowball Dataset" com pares vencedores de boa qualidade
6. **Permite** retreinar Annie com esses novos dados

**Resultado**: Um ciclo virtuoso onde Annie melhora continuamente com dados reais.

---

## 2. Componentes

### A. `arena_ciclo_virtuoso.py` (Principal)
- **Entrada**: CSV exportado do Translator++ (Map002.xlsx - Worksheet.csv)
- **Saída**: 
  - `Map002_Refinado.csv` (para re-importar no Translator++)
  - `dataset_snowball.json` (novos pares para retreino)
- **Fluxo**:
  ```
  CSV (Original, Machine) 
    ↓
  [Máscaras tags] → [Annie] → [Avalia] ← [Rival Online]
    ↓
  Ganhador determinado (Annie vs Online)
    ↓
  CSV atualizado + Snowball Dataset
  ```

### B. `snowball_manager.py` (Utilitário)
Gerencia o Snowball Dataset com 4 ações:
- **validate**: Valida estrutura JSON
- **clean**: Remove duplicatas e scores baixos
- **merge**: Mescla múltiplos snowball datasets
- **stats**: Gera estatísticas e relatórios

### C. `instalar_dependencias_arena.py` (Setup)
Instala todas as dependências necessárias.

---

## 3. Instalação

### Passo 1: Instalar Dependências
```bash
# Opção A: Script automático
python instalar_dependencias_arena.py

# Opção B: Manualmente
pip install -r requirements_arena.txt
```

**Dependências instaladas**:
- `pandas` - Leitura/escrita de CSV
- `openpyxl` - Suporte Excel
- `torch` - Framework para IA
- `transformers` - Modelos Hugging Face
- `torchaudio` - Utilitários

### Passo 2: Verificar Modelos
```bash
# Certifique-se que sua Annie está em ./modelo_annie_v1/
# Certifique-se que TransQuest está disponível (será auto-baixado)
```

---

## 4. Uso Prático

### Fluxo Completo (Passo-a-Passo)

#### 4.1. Preparar Dados no Translator++

1. Abra o Translator++
2. Abra seu mapa de jogo (ex: Map002)
3. Selecione **Batch Translation** → Google Translator (ou Bing)
4. Preencha a coluna "Machine translation" com as traduções online
5. Exporte como CSV:
   - **File** → **Export**
   - **Format**: CSV
   - **Filename**: `Map002.xlsx - Worksheet.csv`
   - **Salve** na pasta do projeto

#### 4.2. Executar a Arena

```bash
# Ative o ambiente virtual
source venv_ia/Scripts/activate  # Linux/Mac
.\venv_ia\Scripts\Activate.ps1    # Windows PowerShell

# Execute a Arena
python arena_ciclo_virtuoso.py
```

**Saída esperada**:
```
======================================================================
ARENA - Ciclo Virtuoso de Treinamento
======================================================================

[1/3] Carregando Annie (MarianMT)...
✓ Annie carregada de: ./modelo_annie_v1

[2/3] Carregando Juiz (TransQuest)...
✓ Juiz (TransQuest) carregado

[3/3] Lendo dados do Translator++...

======================================================================
Iniciando Arena com 150 linhas...
======================================================================

[   10] Processando...
[   20] Processando...
...
[  150] Processando...

======================================================================
RELATÓRIO FINAL
======================================================================
Total de linhas processadas:  150
Linhas vazias ignoradas:      5
Annie venceu:                 85 (58.6%)
Online venceu:                60 (41.4%)
Salvos no Snowball:           32

💡 Próximo passo: Retreinar Annie com o Snowball Dataset
   $ python treinador_nmt.py --dataset dataset_snowball.json --epochs 3

✓ Importe 'Map002_Refinado.csv' no Translator++ para continuar a revisão manual.
======================================================================
```

#### 4.3. Validar Resultados

```bash
# Ver estatísticas do Snowball Dataset
python snowball_manager.py --action stats --file dataset_snowball.json

# Exemplo de saída:
# ============================================================
# ESTATÍSTICAS: dataset_snowball.json
# ============================================================
# Tamanho do dataset: 32 pares
# 
# Comprimento dos textos (palavras):
#   Inglês:  min=3, max=45, média=12.5
#   Português: min=3, max=50, média=13.2
# 
# Origens dos pares:
#   Snowball_Google: 32
# 
# Scores de qualidade (TransQuest):
#   Mínimo: 0.615
#   Máximo: 0.892
#   Média:  0.751
```

#### 4.4. Retreinar Annie (Opcional)

Se tiver novos dados Snowball com boa qualidade:

```bash
python treinador_nmt.py --dataset dataset_snowball.json --epochs 3 --batch-size 16
```

Isso fará Annie aprender com os dados reais do seu jogo.

---

## 5. Configuração Avançada

### A. Alterar Limiares de Qualidade

No `arena_ciclo_virtuoso.py`, linha ~30:

```python
# Limiar de qualidade para salvar no Snowball
LIMIAR_QUALIDADE_SNOWBALL = 0.60  # Aumentar para mais seletivo
```

**Recomendado**:
- `0.50` - Permissivo (salva mais dados, mas qualidade variável)
- `0.60` - Equilibrado (padrão)
- `0.70` - Seletivo (só dados muito bons)
- `0.80` - Ultra-seletivo (apenas ouro puro)

### B. Usar Heurística (sem TransQuest)

Se TransQuest não funcionar, a Arena usa automaticamente heurística baseada em:
- Comprimento similar
- Preservação de pontuação
- Ausência de tags anômalas

Ver `_heuristica_qualidade()` em `arena_ciclo_virtuoso.py`.

### C. Configurar Caminhos Customizados

No `arena_ciclo_virtuoso.py`, linhas ~20-26:

```python
ARQUIVO_ENTRADA = "seu_arquivo.csv"
ARQUIVO_SAIDA = "seu_arquivo_refinado.csv"
CAMINHO_ANNIE = "./seu_modelo_local"
ARQUIVO_TREINO_FUTURO = "seu_dataset_snowball.json"
```

---

## 6. Máscara de Tags (Proteção)

A Arena implementa a técnica de mascaramento de tags descrita no seu PDF:

### Fluxo:

```
Original:     "Hello {i}World{/i}"
      ↓
Mascarado:    "Hello __TAG_0__World__TAG_1__"
      ↓
[Annie vê apenas: "Hello __TAG_0__World__TAG_1__"]
      ↓
Traduzido:    "Olá __TAG_0__Mundo__TAG_1__"
      ↓
Desmascarado: "Olá {i}Mundo{/i}"
```

**Benefício**: Annie não alucina sobre tags, preservando estrutura 100%.

### Tags Capturadas:
- Códigos RPGMaker: `\V[1]`, `\N[2]`, `\C[0]`, `\I[5]`
- Tags Ren'Py: `{i}`, `{/i}`, `{color}`, `{/color}`
- Quebras de linha: `\n`

---

## 7. Troubleshooting

### Erro: "Arquivo não encontrado: Map002.xlsx - Worksheet.csv"

**Solução**:
1. Exporte novamente do Translator++
2. Verifique o nome exato do arquivo
3. Certifique-se que está na pasta correta (junto com o script)

### Erro: "TransQuest não encontrado"

**Solução**:
1. A Arena funcionará com heurística automática (menos precisa)
2. Para usar TransQuest, instale:
   ```bash
   pip install TransQuest
   ```

### Erro: "Annie não carregada"

**Solução**:
1. Verifique se o arquivo está em `./modelo_annie_v1/`
2. Execute:
   ```bash
   ls ./modelo_annie_v1/
   # Deve ter: config.json, model.safetensors, tokenizer_config.json, etc.
   ```

### Snowball Dataset com 0 pares

**Razão**: Limiar de qualidade muito alto ou traduções online todas ruins.

**Solução**:
1. Abaixe `LIMIAR_QUALIDADE_SNOWBALL` para 0.50
2. Re-execute a Arena
3. Verifique manualmente as traduções online no Translator++

---

## 8. Exemplos de Uso Avançado

### Mesclar múltiplos Snowball Datasets

Se rodou Arena em vários mapas:

```bash
python snowball_manager.py --action merge \
  --files Map001_snowball.json Map002_snowball.json Map003_snowball.json \
  --output dataset_snowball_completo.json
```

### Limpar dataset (remover duplicatas)

```bash
python snowball_manager.py --action clean \
  --file dataset_snowball.json \
  --output dataset_snowball_cleaned.json \
  --min-score 0.65
```

### Validar integridade

```bash
python snowball_manager.py --action validate --file dataset_snowball.json
```

---

## 9. Performance & Otimizações

### Tempo de Execução

Para 150 linhas (~típico de um mapa):
- **Com GPU**: ~30-60 segundos
- **Sem GPU (CPU)**: ~2-5 minutos

### Otimizações Possíveis

1. **Reduzir tamanho de batch** (se memória insuficiente):
   ```python
   # No traduzir_annie():
   inputs = tokenizer_annie(..., padding=False)  # Desativa padding
   ```

2. **Usar modelo mais leve** (se muito lento):
   ```python
   CAMINHO_ANNIE = "./modelo_annie_lite"  # Versão leve
   ```

3. **Paralelizar processamento** (avançado):
   ```python
   # Use ProcessPoolExecutor para processar múltiplas linhas em paralelo
   ```

---

## 10. Estrutura do Snowball Dataset

O arquivo `dataset_snowball.json` tem este formato:

```json
[
  {
    "en": "Hello, beautiful world!",
    "pt": "Olá, mundo lindo!",
    "origem": "Snowball_Google",
    "score": 0.752
  },
  {
    "en": "Emotional glee\nIntoxicated, blissful\nAn old soul's rapture",
    "pt": "Alegria emocional\nEmbriagante, bemaventurado\nArrebatamento de uma alma antiga",
    "origem": "Snowball_Google",
    "score": 0.684
  }
]
```

**Campos**:
- `en` - Texto original em inglês
- `pt` - Tradução em português (vencedora)
- `origem` - Sempre "Snowball_Google" (marca de origem)
- `score` - Score de qualidade (0.0-1.0) dado pelo TransQuest

---

## 11. Próximas Etapas

Após executar a Arena:

1. ✅ **Validar Dados** (Translator++ revisor humano)
   ```
   Importe Map002_Refinado.csv no Translator++
   Revise as escolhas (compare Annie vs Online)
   Aprove ou corrija manualmente
   ```

2. ✅ **Retreinar Annie** (Snowball)
   ```bash
   python treinador_nmt.py --dataset dataset_snowball.json --epochs 3
   ```

3. ✅ **Repetir Ciclo** (Arena 2)
   ```
   Exporte novamente do Translator++
   Execute Arena com novos dados
   Annie melhora a cada ciclo
   ```

---

## 12. Suporte & Contribuições

Se encontrar bugs ou tiver sugestões:

1. Verifique o arquivo `assistente_overlay_v3.py` para contexto geral
2. Veja `CIRCUIT_BREAKER_IMPLEMENTATION.md` para arquitectura
3. Consulte `INDEX.md` para mapa do repositório completo

---

**Última Atualização**: 2025-12-10
**Versão**: 1.0-Arena
**Status**: Produção

