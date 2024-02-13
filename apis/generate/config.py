from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_GENERATE_URL_PREFIX: str = "generate"
    API_GENERATE_MODEL_NAME: str = "bigscience/bloom-1b1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
