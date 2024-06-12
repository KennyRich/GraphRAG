import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_EMBEDDING_ENDPOINT = "https://api.openai.com/v1/embeddings"
    PYDATA_API_KEY = os.getenv('PYDATA_API_KEY')


settings = Settings()
