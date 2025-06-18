import requests
from flask import current_app
import json

def generate_quiz(prompt):
    API_KEY = current_app.config.get("GEN_AI_API_KEY")
    API_URL = "https://api.together.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # Append additional instructions to force JSON output
    full_prompt = (
        prompt + "\n\n" +
        "Return only a valid JSON object with no extra text. " +
        "The JSON should have a key 'questions' containing a list of 5 questions. " +
        "Each question must be an object with three keys: " +
        "'question' (the question text), " +
        "'options' (a list of 4 option strings), and " +
        "'answer' (the letter corresponding to the correct option, e.g., 'A')."
    )

    data = {
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "messages": [{"role": "user", "content": full_prompt}]
    }

    response = requests.post(API_URL, headers=headers, json=data)

    if response.status_code == 200:
        try:
            resp_json = response.json()
            # Extract the content from the AI response
            quiz_text = resp_json["choices"][0]["message"]["content"]
            # Try to parse the returned text as JSON.
            try:
                parsed = json.loads(quiz_text)
                # If successful, return the JSON string
                return json.dumps(parsed)
            except Exception:
                # If parsing fails, return the raw text so you know what was generated
                return quiz_text
        except Exception as e:
            return f"Error processing AI response: {str(e)}"
    else:
        return f"Error: {response.status_code} {response.json()}"
