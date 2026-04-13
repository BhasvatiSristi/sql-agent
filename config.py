"""
config.py
=========
All project settings live here.
Change the model, DB path, or verbosity in exactly one place.
"""

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env files

# ── Database ──────────────────────────────────────────────────────────────────
# Path to your existing SQLite database file.
# Place orders.db in the same directory as this project, or set the full path.
DB_PATH = "orders.db"

# ── LLM ───────────────────────────────────────────────────────────────────────
# Mistral model to use.
# Good options (in order of capability):
#   "mistral-large-latest"   → Best reasoning, best SQL accuracy (recommended)
#   "mistral-small-latest"   → Faster and cheaper, good for testing
MODEL_NAME = "mistral-large-latest"

# temperature=0 means fully deterministic — no creative guessing.
# Always use 0 for SQL agents: we need precision, not creativity.
TEMPERATURE = 0

# ── Agent behaviour ───────────────────────────────────────────────────────────
# VERBOSE = True  → prints every Thought / Action / Observation step.
#                   Use this while learning — it's the whole point.
# VERBOSE = False → silent until the final answer. Use in production.
VERBOSE = True

# ── API Key ───────────────────────────────────────────────────────────────────
# Load from environment variable — never hardcode secrets in source files.
#
# Set it before running:
#   macOS/Linux:  export MISTRAL_API_KEY="your-key-here"
#   Windows CMD:  set MISTRAL_API_KEY=your-key-here
#
# Get your key at: https://console.mistral.ai/
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    raise EnvironmentError(
        "\n[CONFIG ERROR] MISTRAL_API_KEY environment variable is not set.\n"
        "Run:  export MISTRAL_API_KEY='your-key-here'\n"
        "Get your key at: https://console.mistral.ai/\n"
    )