import os
import json
import yaml
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
PROMPTS_FILE = 'backend/prompts.yml'


def load_prompts() -> dict:
    """Load prompts from YAML file."""
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def answer_question(question: str, sheet_data: list) -> str:
    """
    Takes a natural language question and the sheet data,
    returns an answer from Groq LLM.

    sheet_data is a list of dicts — one per job application row.
    """
    try:
        prompts = load_prompts()
        chat_prompt = prompts['dashboard_chat']

        # Format sheet data as clean JSON for the LLM
        sheet_json = json.dumps(sheet_data, indent=2, ensure_ascii=False)

        # Fill in prompt template
        system_prompt = chat_prompt['system'].format(
            today=datetime.now().strftime('%Y-%m-%d')
        )

        user_prompt = chat_prompt['user'].format(
            sheet_data=sheet_json,
            question=question
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Sorry, I couldn't process your question: {str(e)}"