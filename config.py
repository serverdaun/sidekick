import os

from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_CHAT_MODEL_WORKER = os.getenv("OPENAI_CHAT_MODEL_WORKER", "gpt-4o-mini")
OPENAI_CHAT_MODEL_EVALUATOR = os.getenv("OPENAI_CHAT_MODEL_EVALUATOR", "gpt-4o-mini")
MEMORY_FILE = os.getenv("MEMORY_FILE", "sidekick_memory.json")
