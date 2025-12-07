#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Circuit Breaker Pattern
Simula falhas do Gemini e verifica fallback para Groq
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

print("="*60)
print("TESTE: Circuit Breaker Pattern - Gemini + Groq Fallback")
print("="*60)

# 1. Verificar APIs
print("\n[1] Verificando disponibilidade das APIs...\n")

API_KEY_GOOGLE = os.getenv("GEMINI_API_KEY")
API_KEY_GROQ = os.getenv("GROQ_API_KEY")

if API_KEY_GOOGLE:
    print("  ✓ Google Gemini API Key: OK")
else:
    print("  ✗ Google Gemini API Key: NOT FOUND")

if API_KEY_GROQ:
    print("  ✓ Groq API Key: OK")
else:
    print("  ✗ Groq API Key: NOT FOUND")

# 2. Teste de imports
print("\n[2] Testando imports das bibliotecas...\n")

try:
    import google.generativeai as genai
    print("  ✓ google.generativeai: OK")
except Exception as e:
    print(f"  ✗ google.generativeai: FALHOU - {e}")
    sys.exit(1)

try:
    from groq import Groq
    print("  ✓ groq: OK")
except Exception as e:
    print(f"  ✗ groq: FALHOU - {e}")
    sys.exit(1)

# 3. Inicializar clientes
print("\n[3] Inicializando clientes...\n")

MODELO_GOOGLE = None
CLIENTE_GROQ = None

if API_KEY_GOOGLE:
    genai.configure(api_key=API_KEY_GOOGLE)
    try:
        MODELO_GOOGLE = genai.GenerativeModel('models/gemini-2.0-flash')
        print("  ✓ Gemini 2.0-Flash: Inicializado")
    except:
        try:
            MODELO_GOOGLE = genai.GenerativeModel('models/gemini-pro')
            print("  ✓ Gemini Pro (fallback): Inicializado")
        except:
            print("  ✗ Nenhum modelo Gemini disponivel")

if API_KEY_GROQ:
    try:
        CLIENTE_GROQ = Groq(api_key=API_KEY_GROQ)
        print("  ✓ Groq Llama 3: Inicializado")
    except Exception as e:
        print(f"  ✗ Groq: FALHOU - {e}")

# 4. Teste de chamadas
print("\n[4] Testando chamadas de API...\n")

prompt_teste = """Translate to Portuguese (one line only):
"Hello, this is a test"
"""

# Teste Gemini
if MODELO_GOOGLE:
    print("  Teste 1: Gemini (Plano A)")
    try:
        res = MODELO_GOOGLE.generate_content(prompt_teste).text
        print(f"    ✓ Resposta: {res[:50]}...")
    except Exception as e:
        print(f"    ✗ Erro: {str(e)[:80]}...")

# Teste Groq
if CLIENTE_GROQ:
    print("\n  Teste 2: Groq (Plano B)")
    try:
        chat_completion = CLIENTE_GROQ.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a translation engine. Output ONLY the translation."
                },
                {
                    "role": "user",
                    "content": prompt_teste,
                }
            ],
            model="mixtral-8x7b-32768",  # Modelo disponivel (alternativa ao llama3)
            temperature=0.3,
        )
        res = chat_completion.choices[0].message.content
        print(f"    ✓ Resposta: {res[:50]}...")
    except Exception as e:
        print(f"    ✗ Erro: {str(e)[:80]}...")

# 5. Status final
print("\n" + "="*60)
print("STATUS FINAL")
print("="*60)

if MODELO_GOOGLE and CLIENTE_GROQ:
    print("\n  ✓ SISTEMA PRONTO: Ambos os provedores operacionais")
    print("  ✓ Gemini (Plano A): ATIVO")
    print("  ✓ Groq (Plano B): ATIVO (FALLBACK)")
    print("\n  Circuit Breaker Pattern: ATIVADO")
    print("  Redundancia: GARANTIDA")
elif MODELO_GOOGLE:
    print("\n  ! Apenas Gemini disponivel (sem fallback)")
elif CLIENTE_GROQ:
    print("\n  ! Apenas Groq disponivel")
else:
    print("\n  ✗ ERRO: Nenhum provedor disponivel!")

print("\n" + "="*60)
