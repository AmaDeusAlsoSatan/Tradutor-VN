import json
import os
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, DataCollatorForSeq2Seq, Seq2SeqTrainingArguments, Seq2SeqTrainer

os.environ["WANDB_DISABLED"] = "true"

# --- CONFIGURAÇÕES ---
# Agora usamos o OURO (Sua correção manual perfeita)
ARQUIVO_DATASET = "dataset_master_gold.json" 
MODELO_BASE = "Helsinki-NLP/opus-mt-en-ROMANCE" 
PASTA_SAIDA = "./modelo_annie_v1" # Vai sobrescrever/atualizar a Annie atual

def treinar_modelo():
    print(f"--- Iniciando Treinamento da Annie com {ARQUIVO_DATASET} ---")

    if not os.path.exists(ARQUIVO_DATASET):
        print("Erro: Arquivo de Ouro não encontrado.")
        return

    # Carrega os dados
    with open(ARQUIVO_DATASET, "r", encoding="utf-8") as f:
        dados_raw = json.load(f)
    
    # Filtra apenas dados válidos
    dados_limpos = [{"en": d["en"], "pt": d["pt"]} for d in dados_raw if d["score"] >= 90]
    print(f"Frases de Alta Qualidade carregadas: {len(dados_limpos)}")
    
    if len(dados_limpos) < 10:
        print("⚠️ Poucos dados para treino. Recomendo pelo menos 50 frases.")
        # Continua mesmo assim para teste, mas avisa.

    dataset = Dataset.from_list(dados_limpos)
    dataset = dataset.train_test_split(test_size=0.1) # 10% para prova final

    print("Carregando Cérebro Atual...")
    # Tenta carregar a Annie V1 se existir, senão baixa o base
    caminho_carga = PASTA_SAIDA if os.path.exists(PASTA_SAIDA) else MODELO_BASE
    tokenizer = AutoTokenizer.from_pretrained(caminho_carga)
    model = AutoModelForSeq2SeqLM.from_pretrained(caminho_carga)

    def preprocessar(exemplos):
        inputs = [">>pt<< " + ex for ex in exemplos["en"]]
        targets = exemplos["pt"]
        model_inputs = tokenizer(inputs, max_length=128, truncation=True)
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=128, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized_datasets = dataset.map(preprocessar, batched=True)

    args = Seq2SeqTrainingArguments(
        output_dir=PASTA_SAIDA,
        do_eval=False,
        learning_rate=2e-5,
        per_device_train_batch_size=4,
        num_train_epochs=3, # Treino rápido para não esquecer o português geral
        weight_decay=0.01,
        save_total_limit=2,
        predict_with_generate=True
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        tokenizer=tokenizer,
    )

    print("--- Treinando... (A Annie está estudando suas correções) ---")
    trainer.train()
    
    print("Salvando nova versão da Annie...")
    model.save_pretrained(PASTA_SAIDA)
    tokenizer.save_pretrained(PASTA_SAIDA)
    print("--- CONCLUSÃO: Annie subiu de nível! ---")

if __name__ == "__main__":
    treinar_modelo()
