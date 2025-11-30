import json
import os
from datasets import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSeq2SeqLM, 
    DataCollatorForSeq2Seq, 
    Seq2SeqTrainingArguments, 
    Seq2SeqTrainer
)

# --- CONFIGURAÇÕES ---
ARQUIVO_DATASET = "dataset_treino.json"
# CORREÇÃO: Usando o modelo "Romance" que inclui Português (o en-pt não existe isolado)
MODELO_BASE = "Helsinki-NLP/opus-mt-en-ROMANCE" 
PASTA_SAIDA = "./modelo_annie_v1"

def treinar_modelo():
    print("--- Iniciando a Fábrica de Tradução (Fine-Tuning NMT) ---")

    if not os.path.exists(ARQUIVO_DATASET):
        print(f"Erro: {ARQUIVO_DATASET} não encontrado.")
        return

    print("Carregando dados...")
    with open(ARQUIVO_DATASET, "r", encoding="utf-8") as f:
        dados = json.load(f)
    
    dataset_bruto = Dataset.from_list(dados)
    dataset_dividido = dataset_bruto.train_test_split(test_size=0.1)
    
    print(f"Baixando modelo base: {MODELO_BASE}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODELO_BASE)
        modelo = AutoModelForSeq2SeqLM.from_pretrained(MODELO_BASE)
    except Exception as e:
        print(f"ERRO AO BAIXAR MODELO: {e}")
        return

    # 3. Preparar os dados (Tokenização com Target Language)
    def preprocessar(exemplos):
        # TRUQUE DE MESTRE: Adicionamos ">>pt<< " antes da frase em inglês.
        # Isso diz ao modelo multilingue: "Traduza isso para PORTUGUÊS".
        inputs = [">>pt<< " + ex for ex in exemplos["en"]]
        targets = exemplos["pt"]
        
        model_inputs = tokenizer(inputs, max_length=128, truncation=True)
        
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=128, truncation=True)

        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    print("Processando frases...")
    tokenized_datasets = dataset_dividido.map(preprocessar, batched=True)

    # 4. Configurar o Treinamento (Ajustado para CPU)
    args = Seq2SeqTrainingArguments(
        output_dir=PASTA_SAIDA,
        # evaluation_strategy="epoch", # Removido devido a incompatibilidade com a versão atual do transformers
        learning_rate=2e-5,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        weight_decay=0.01,
        save_total_limit=2,
        num_train_epochs=5, # Aumentei para 5 épocas para ele aprender bem
        predict_with_generate=True,
        use_cpu=True
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=modelo)

    trainer = Seq2SeqTrainer(
        model=modelo,
        args=args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    print("--- Começando o Treinamento (Isso pode demorar alguns minutos) ---")
    trainer.train()

    print(f"Salvando o seu modelo personalizado em: {PASTA_SAIDA}")
    modelo.save_pretrained(PASTA_SAIDA)
    tokenizer.save_pretrained(PASTA_SAIDA)
    
    print("\n--- SUCESSO! O modelo nasceu. ---")

if __name__ == "__main__":
    treinar_modelo()
