"""Configuration — reads API keys from environment / Codespaces secrets."""
import os
from pathlib import Path

PROJECT_ROOT = Path("/workspaces/specforge")
RAFT_DIR     = PROJECT_ROOT / "raft.tla"
TLC_JAR      = PROJECT_ROOT / "tla2tools.jar"
RESULTS_DIR  = PROJECT_ROOT / "results"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")

GEMINI_MODEL = "gemini-3.8-flash"
GROQ_MODEL   = "openai/gpt-oss-120b"

MAX_ATTEMPTS = 4
TLC_TIMEOUT_SECONDS = 60

def check_keys():
    ok = True
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY not set")
        ok = False
    else:
        print(f"✓ Gemini key set (model: {GEMINI_MODEL})")
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not set")
        ok = False
    else:
        print(f"✓ Groq key set (model: {GROQ_MODEL})")
    return ok

if __name__ == "__main__":
    check_keys()

# Second comparison model (Qwen — different family, smaller)
QWEN_MODEL = "qwen/qwen3.8-27b"
