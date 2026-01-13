"""Constants for AI services."""

# LLM Configuration
MODEL_NAME = "gemini-3-flash-preview"
TEMPERATURE = 0.2  # Low temperature for consistency

# Classification Configuration
MAX_TOPICS_PER_ITEM = 5
MIN_CLASSIFICATION_SCORE = 0.5

# Processing Configuration
BATCH_SIZE = 10  # Items per batch
RATE_LIMIT_DELAY = 1  # Seconds between API calls

# Retry Configuration
MAX_RETRIES = 1
RETRY_DELAY = 2  # Seconds
