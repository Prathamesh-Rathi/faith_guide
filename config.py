import os

class Config:
    SECRET_KEY       = os.environ.get('SECRET_KEY', 'faithguide-secret-key-2025')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///faithguide.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', 'API key')
    GROQ_MODEL   = 'llama-3.1-8b-instant'

    # ── Image Generation ─────────────────────────────────────────────────────
    # Primary: Hugging Face (free, reliable)
    HF_API_KEY   = os.environ.get('HF_API_KEY', 'API key')
    HF_MODEL_URL = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0'

    # Fallback: Pollinations
    IMAGE_API_URL = 'https://image.pollinations.ai/prompt/'

    CHROMA_DB_PATH    = './data/chroma_db'
    CHROMA_COLLECTION = 'bible_verses'

    TOP_K_VERSES    = 5
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

    DENOMINATIONS = [
        'Protestant (General)', 'Catholic', 'Orthodox',
        'Baptist', 'Methodist', 'Lutheran',
        'Pentecostal', 'Anglican / Episcopal',
    ]

    MAX_CONVERSATION_HISTORY = 20
    CONTENT_SAFETY_THRESHOLD = 0.7