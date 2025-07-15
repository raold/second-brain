import os

from dotenv import load_dotenv

# Load .env file if present (useful in local dev)
load_dotenv()

class Config:
    # === OpenAI Settings ===
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # === API Authentication ===
    API_TOKENS = os.getenv("API_TOKENS", "").split(",")

    # === Qdrant Settings ===
    QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "second_brain")
    QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", 1536))
    QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")

    # === Logging ===
    LOG_PATH = os.getenv("LOG_PATH", "tests/logs/processor.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # === OpenAI Retry Settings ===
    OPENAI_RETRY_ATTEMPTS = int(os.getenv("OPENAI_RETRY_ATTEMPTS", 3))
    OPENAI_RETRY_MULTIPLIER = int(os.getenv("OPENAI_RETRY_MULTIPLIER", 1))
    OPENAI_RETRY_MIN_WAIT = int(os.getenv("OPENAI_RETRY_MIN_WAIT", 2))
    OPENAI_RETRY_MAX_WAIT = int(os.getenv("OPENAI_RETRY_MAX_WAIT", 10))

    # === Model Version Tracking ===
    MODEL_VERSIONS = {
        "llm": os.getenv("MODEL_VERSION_LLM", "gpt-4o"),
        "embedding": os.getenv("MODEL_VERSION_EMBEDDING", "text-embedding-3-small")
    }

    @classmethod
    def summary(cls):
        return {
            "openai_model": cls.OPENAI_EMBEDDING_MODEL,
            "qdrant_host": cls.QDRANT_HOST,
            "qdrant_port": cls.QDRANT_PORT,
            "qdrant_collection": cls.QDRANT_COLLECTION,
            "log_path": cls.LOG_PATH,
            "log_level": cls.LOG_LEVEL,
            "retry_attempts": cls.OPENAI_RETRY_ATTEMPTS
        }
