from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_ZEROSHOT_URL_PREFIX: str = "zeroshot"
    API_ZEROSHOT_MODEL_NAME: str = "Recognai/zeroshot_selectra_small"
    TRANSFORMERS_CACHE: str = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
