"""
config.py
=========
All project settings live here.
Change the model, DB path, or verbosity in exactly one place.
"""

import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env files

DB_PATH = "orders.db"

#   "mistral-large-latest"   → Best reasoning, best SQL accuracy (recommended)
#   "mistral-small-latest"   → Faster and cheaper, good for testing
MODEL_NAME = "mistral-small-latest"

TEMPERATURE = 0

VERBOSE = True

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    raise EnvironmentError(
        "\n[CONFIG ERROR] MISTRAL_API_KEY environment variable is not set.\n"
        "Run:  export MISTRAL_API_KEY='your-key-here'\n"
        "Get your key at: https://console.mistral.ai/\n"
    )