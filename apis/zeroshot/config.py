from pydantic import BaseSettings


class Settings(BaseSettings):
    API_ZEROSHOT_URL_PREFIX = "zeroshot"
    API_ZEROSHOT_MODEL_NAME = "Recognai/zeroshot_selectra_small"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
