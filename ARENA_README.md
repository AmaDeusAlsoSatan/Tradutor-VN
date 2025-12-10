# ARENA - Quick Start Guide

## O que você tem agora?

Implementamos 3 scripts completos + documentação para o **Ciclo Virtuoso de Treinamento**:

### 📋 Scripts Principais

| Script | Função | Entrada | Saída |
|--------|--------|---------|-------|
| `arena_ciclo_virtuoso.py` | Motor principal da Arena | CSV do Translator++ | CSV refinado + Snowball Dataset |
| `snowball_manager.py` | Gerenciador de datasets | JSON Snowball | Validação/limpeza/merge |
| `instalar_dependencias_arena.py` | Setup automático | - | Dependências instaladas |

### 📁 Arquivos Gerados

- `ARENA_GUIA_COMPLETO.md` - Documentação detalhada (12 seções)
- `requirements_arena.txt` - Dependências pip
- `exemplo_entrada_arena.csv` - Dados de teste

---

## ⚡ Início Rápido (5 minutos)

### 1. Instalar Dependências
```bash
# Ative o venv_ia
.\venv_ia\Scripts\Activate.ps1

# Instale tudo
python instalar_dependencias_arena.py
```

### 2. Testar com Exemplo
```bash
# Copie o exemplo
copy exemplo_entrada_arena.csv "Map002.xlsx - Worksheet.csv"

# Execute a Arena
python arena_ciclo_virtuoso.py
```

### 3. Usar com Dados Reais
```bash
# Exporte do Translator++ como CSV
# Nomeie como: Map002.xlsx - Worksheet.csv
# Coloque na pasta do projeto
# Execute: python arena_ciclo_virtuoso.py
```

### 4. Validar Resultados
```bash
# Ver estatísticas do Snowball gerado
python snowball_manager.py --action stats --file dataset_snowball.json
```

### 5. Retreinar Annie (Opcional)
```bash
# Se tiver novos dados com qualidade > 0.6
python treinador_nmt.py --dataset dataset_snowball.json --epochs 3
```

---

## 🎯 O que Cada Script Faz

### `arena_ciclo_virtuoso.py`

**Fluxo**:
```
CSV (Original + Machine) 
  ↓
[Máscara de Tags] 
  ↓
Annie vs Google/Bing (com TransQuest como juiz)
  ↓
CSV atualizado (melhor tradução em cada linha)
  ↓
dataset_snowball.json (pares de boa qualidade para retreino)
```

**Máscara de Tags**: 
- Substitui `{i}`, `{/i}`, `\n`, `\V[1]`, etc. por tokens seguros
- Annie traduz sem alucinar sobre tags
- Tags são restauradas na saída

### `snowball_manager.py`

Gerencia o `dataset_snowball.json`:
- ✅ `--action validate` - Valida estrutura
- ✅ `--action clean` - Remove duplicatas e scores baixos
- ✅ `--action merge` - Mescla múltiplos datasets
- ✅ `--action stats` - Gera relatório de qualidade

### `instalar_dependencias_arena.py`

Instala automaticamente:
- `pandas` - Leitura CSV
- `openpyxl` - Suporte Excel
- `torch` - Framework
- `transformers` - Modelos
- `torchaudio` - Utilitários

---

## 📊 Exemplo de Saída

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
Iniciando Arena com 10 linhas...
======================================================================

[   10] Processando...

======================================================================
RELATÓRIO FINAL
======================================================================
Total de linhas processadas:  10
Linhas vazias ignoradas:      0
Annie venceu:                 6 (60.0%)
Online venceu:                4 (40.0%)
Salvos no Snowball:           2

💡 Próximo passo: Retreinar Annie com o Snowball Dataset
   $ python treinador_nmt.py --dataset dataset_snowball.json --epochs 3

✓ Importe 'Map002_Refinado.csv' no Translator++ para continuar a revisão manual.
```

---

## 🔧 Configurações Principais

No `arena_ciclo_virtuoso.py` (linhas ~20-26):

```python
# Entrada/Saída
ARQUIVO_ENTRADA = "Map002.xlsx - Worksheet.csv"  # CSV do Translator++
ARQUIVO_SAIDA = "Map002_Refinado.csv"            # CSV atualizado
CAMINHO_ANNIE = "./modelo_annie_v1"              # Seu modelo
ARQUIVO_TREINO_FUTURO = "dataset_snowball.json"  # Dados de retreino

# Qualidade
LIMIAR_QUALIDADE_SNOWBALL = 0.60  # Aumentar para mais seletivo (0.70, 0.80)
```

---

## ⚙️ Requisitos

- ✅ Python 3.8+
- ✅ `modelo_annie_v1/` (seu MarianMT fine-tuned)
- ✅ CSV exportado do Translator++ (com coluna "Machine translation" preenchida)
- ✅ Pelo menos 2GB RAM (4GB recomendado)
- ✅ GPU opcional (melhor performance)

---

## 🐛 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| "Arquivo não encontrado" | Exporte novamente do Translator++ como CSV |
| "Annie não carregada" | Verifique se está em `./modelo_annie_v1/` |
| "TransQuest não disponível" | Usa heurística automática (menos precisa) |
| "0 pares no Snowball" | Abaixe `LIMIAR_QUALIDADE_SNOWBALL` para 0.50 |

---

## 📖 Documentação Completa

Leia `ARENA_GUIA_COMPLETO.md` para:
- 12 seções detalhadas
- Fluxos de trabalho passo-a-passo
- Configurações avançadas
- Performance & otimizações
- Exemplos de uso
- Troubleshooting extenso

---

## 🎓 Conceitos-Chave

### Ciclo Virtuoso (Snowball)
```
Arena 1: Annie 60% vs Google 40% → Snowball Dataset criado
   ↓
Retreinar Annie com Snowball
   ↓
Arena 2: Annie 75% vs Google 25% → Melhores Snowball dados
   ↓
Retreinar Annie novamente
   ↓
Arena 3: Annie 85% vs Google 15% → Annie é praticamente melhor
```

### Máscara de Tags
```
Sem máscara: Annie pode alucinar sobre {i}, {/i}
Com máscara: Annie vê __TAG_0__, __TAG_1__ e traduz com confiança
```

### TransQuest (Juiz)
```
Avalia: "Original [SEP] Tradução" → Score 0.0-1.0
Mais alto = melhor qualidade
```

---

## ✅ Checklist de Implementação

- ✅ Script principal (`arena_ciclo_virtuoso.py`) - 600+ linhas
- ✅ Gerenciador Snowball (`snowball_manager.py`) - 400+ linhas
- ✅ Instalador automático (`instalar_dependencias_arena.py`)
- ✅ Documentação completa (`ARENA_GUIA_COMPLETO.md`)
- ✅ Requirements.txt (`requirements_arena.txt`)
- ✅ Dados de teste (`exemplo_entrada_arena.csv`)
- ✅ Máscara de tags (proteção de {i}, {/i}, \n)
- ✅ Suporte TransQuest + Heurística
- ✅ Relatórios detalhados
- ✅ Tratamento de erros robusto

---

## 🚀 Próximos Passos

1. **Execute a instalação**: `python instalar_dependencias_arena.py`
2. **Teste com exemplo**: `copy exemplo_entrada_arena.csv "Map002.xlsx - Worksheet.csv" && python arena_ciclo_virtuoso.py`
3. **Valide**: `python snowball_manager.py --action stats --file dataset_snowball.json`
4. **Retreine** (se houver dados): `python treinador_nmt.py --dataset dataset_snowball.json --epochs 3`
5. **Repita ciclo** com novos mapas

---

**Status**: ✅ COMPLETO E PRONTO PARA PRODUÇÃO
**Última Atualização**: 2025-12-10
**Versão**: 1.0-Arena

