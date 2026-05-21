"""Central configuration for the Hospital AI Assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# --- Model Config ---
LLM_MODEL = "deepseek/deepseek-chat-v3-0324"
LLM_MODEL_FAST = "deepseek/deepseek-chat-v3-0324"
TEMPERATURE = 0.3

# --- RAG Config ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_COLLECTION = "hospital_knowledge"
CHROMA_PERSIST_DIR = "./data/chroma_db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RETRIEVAL = 3

# --- Agent Config ---
MAX_AGENT_STEPS = 5
ESCALATION_KEYWORDS = [
    "chest pain",
    "heart attack",
    "stroke",
    "bleeding",
    "unconscious",
    "breathing difficulty",
    "seizure",
    "ألم في الصدر",
    "نوبة قلبية",
    "نزيف",
    "إغماء",
]

# --- Eval Config ---
EVAL_THRESHOLD_ESCALATION = 0.95
EVAL_THRESHOLD_RETRIEVAL = 0.80
EVAL_THRESHOLD_TOOL_SELECTION = 0.90
