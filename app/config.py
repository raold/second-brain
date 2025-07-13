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
    LOG_PATH = os.getenv("LOG_PATH", "logs/processor.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def summary(cls):
        return {
            "openai_model": cls.OPENAI_EMBEDDING_MODEL,
            "qdrant_host": cls.QDRANT_HOST,
            "qdrant_port": cls.QDRANT_PORT,
            "qdrant_collection": cls.QDRANT_COLLECTION,
            "log_path": cls.LOG_PATH,
            "log_level": cls.LOG_LEVEL
        }
