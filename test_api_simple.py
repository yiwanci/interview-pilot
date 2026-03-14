import os
from pathlib import Path
import sys
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv()

print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"QWEN_API_KEY present: {'Yes' if os.getenv('QWEN_API_KEY') else 'No'}")

from config import get_llm_config

config = get_llm_config()
print(f"Config: {config}")

from openai import OpenAI

client = OpenAI(
    api_key=config["api_key"],
    base_url=config["base_url"],
)

print(f"Testing model: {config['model']}")

try:
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.1,
        max_tokens=10,
    )
    print(f"Success: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()