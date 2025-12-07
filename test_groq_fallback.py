#!/usr/bin/env python3
"""Teste rápido do fallback Groq com llama-3.1-8b-instant"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ GROQ_API_KEY não configurada no .env")
    exit(1)

client = Groq(api_key=api_key)

try:
    print("🧪 Testando Groq Fallback com llama-3.1-8b-instant...")
    
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a translation engine. Output ONLY the requested translation/options. No chat, no notes."
            },
            {
                "role": "user",
                "content": 'Translate to Portuguese: "Hello, world!"'
            }
        ],
        model="llama-3.1-8b-instant",
        temperature=0.3,
    )
    
    result = response.choices[0].message.content
    print(f"✅ Groq respondeu: {result}")
    print("✅ Circuit Breaker Fallback está funcionando!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
