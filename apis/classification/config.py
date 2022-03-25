from pydantic import BaseSettings


class Settings(BaseSettings):
    API_CLASSIFICATION_URL_PREFIX = "classify"
    API_CLASSIFICATION_MODEL_NAME = "pysentimiento/robertuito-sentiment-analysis"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
