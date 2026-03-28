import os
from dotenv import load_dotenv

load_dotenv()

# Obligatoire
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
HUNTER_API_KEY: str = os.getenv("HUNTER_API_KEY", "")

# Sécurité
API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "")

# Modèle
MODEL: str = os.getenv("MODEL", "claude-opus-4-6")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "15"))

# Serveur
PORT: int = int(os.getenv("PORT", "8000"))
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Rate limiting
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
