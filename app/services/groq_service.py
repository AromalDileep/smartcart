import requests
from app.core.config import settings

MODEL_NAME = "llama-3.3-70b-versatile"

def ask_groq_question(context: str, question: str) -> dict:
    """
    Sends a question with product context to the Groq API (LLaMA-3 model)
    and returns the generated answer.
    """
    try:
        system_prompt = (
            "You are a helpful shopping assistant. Use only the information "
            "from the product context. Answer clearly and concisely."
        )

        user_prompt = f"""
Product Context:
{context}

Question: {question}
"""

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

        response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload, timeout=20)
        data = response.json()

        if "choices" in data:
            return {"answer": data["choices"][0]["message"]["content"]}

        return {"error": f"Groq error: {data}"}
    except Exception as e:
        return {"error": str(e)}
