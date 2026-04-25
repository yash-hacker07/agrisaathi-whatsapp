import os
from typing import Optional
from .config import settings

def get_llm_response(prompt: str, system_prompt: str = "You are AgriSaathi, an expert AI agricultural advisor. Be concise, helpful, and friendly.") -> str:
    # 1. Try Groq (Fastest)
    if settings.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Groq failed: {e}. Falling back to basic logic...")

    # 2. Fallback
    return "I am currently running in offline mode. Please check your Groq API key in the .env file."
