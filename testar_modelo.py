from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# --- CONFIGURAÇÃO ---
CAMINHO_MODELO = "./modelo_annie_v1" # A pasta que o treinamento criou

def carregar_tradutor():
    print(f"--- Carregando seu modelo pessoal de: {CAMINHO_MODELO} ---")
    try:
        # Carrega o cérebro que você treinou
        tokenizer = AutoTokenizer.from_pretrained(CAMINHO_MODELO)
        model = AutoModelForSeq2SeqLM.from_pretrained(CAMINHO_MODELO)
        return tokenizer, model
    except Exception as e:
        print(f"Erro ao carregar modelo: {e}")
        print("Verifique se a pasta 'modelo_annie_v1' existe e tem arquivos dentro.")
        return None, None

def traduzir(texto, tokenizer, model):
    # O SEGREDO: Lembra do >>pt<< ? Temos que colocar aqui também.
    # Se não colocar, ele pode traduzir para Espanhol ou Francês.
    texto_preparado = ">>pt<< " + texto
    
    # Transforma texto em números (Tensores)
    inputs = tokenizer(texto_preparado, return_tensors="pt", padding=True)
    
    # A Mágica (Geração)
    # num_beams=5 faz ele testar 5 caminhos diferentes e escolher o melhor (mais qualidade)
    translated_tokens = model.generate(**inputs, max_length=128, num_beams=5, early_stopping=True)
    
    # Transforma números de volta em texto
    resultado = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    return resultado

def iniciar_chat():
    tokenizer, model = carregar_tradutor()
    if not tokenizer: return

    print("\n--- TESTE DE TRADUÇÃO NEURAL (Digite 'sair' para fechar) ---")
    print("O modelo está pronto. Digite uma frase em inglês da VN (ou qualquer outra).")

    while True:
        texto_original = input("\nInglês: ")
        if texto_original.lower() in ['sair', 'exit', 'quit']:
            break
        
        traducao = traduzir(texto_original, tokenizer, model)
        print(f"Português: {traducao}")

if __name__ == "__main__":
    iniciar_chat()
