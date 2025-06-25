---
title: Ai Sidekick
emoji: 🌍
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# AI Sidekick

## Overview
AI Sidekick is an autonomous "co-worker" that can collaborate with you on almost any knowledge-working task.  
Under the hood it combines:
* **LangGraph** – orchestrates a two-node graph consisting of a **worker** agent that tries to complete your task and an **evaluator** agent that inspects the worker's answers against the success criteria you provide.
* **LangChain** tools – web search, Wikipedia, ArXiv, file-system access, a Python REPL, safe symbolic math and a fully-featured Chromium browser driven through Playwright.
* **Gradio** – delivers a clean, one-page chat interface so you can talk to the sidekick in your browser.

The result is a self-reflective assistant able to:
1. Use the above tools to gather information, crunch numbers or automate the browser.
2. Evaluate its own answers and iterate until the predefined success criteria are met.

All conversations (and any artefacts it writes to the `sandbox/` directory) are saved locally so the context persists between sessions.

## Installation
### Prerequisites
* Python **3.12+** (matching the constraint in `pyproject.toml`)
* An OpenAI API key stored as the environment variable `OPENAI_API_KEY`
* Optional – to change the LLM models set `OPENAI_CHAT_MODEL_WORKER` and `OPENAI_CHAT_MODEL_EVALUATOR`.

### Steps
```bash
# 1. Clone the repo
git clone https://github.com/your-org/ai_sidekick.git
cd ai_sidekick

# 2. Install uv
pip install uv

# 3. Create and sync venv
uv sync

# 4. Activate the enviroment
source .venv/bin/activate # .venv/Scripts/activate

# 5. Create a .env file for your keys
cp .env.example .env  # then edit the values
```

## Usage
Start the Gradio application:
```bash
uv run app.py
```
This will launch a local web server (by default at `http://localhost:7860`) presenting the chat UI.

1. Type your request in the *Your request to the Sidekick* box.
2. Optionally describe what "done" looks like in the *success criteria* field. The evaluator agent will use this text to decide when to stop.
3. Press **Go!** and watch the conversation unfold.

UI tips:
* **Reset** – clears the current chat but keeps the long-term memory on disk.
* **Clear Memory** – deletes `sidekick_memory.json` and starts a completely fresh session.

### Programmatic access
If you want to embed the sidekick in your own code you can import the `Sidekick` class:
```python
from sidekick import Sidekick

sidekick = Sidekick()
await sidekick.setup()
result = await sidekick.run_superstep(
    "Write a short poem about the sea",
    success_criteria="The poem is exactly four lines long.",
    history=[],
)
print(result[-2]["content"])  # assistant's reply
```
