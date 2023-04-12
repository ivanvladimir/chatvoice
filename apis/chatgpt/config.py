from pydantic import BaseSettings


class Settings(BaseSettings):
    API_CHATGPT_KEY = "USE_THIS_VARIABLE_TO_SPECIFY_YOUR_KEY_DO_IT_IN_THE_FILE"
    API_CHATGPT_URL_PREFIX = "/chatgpt"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
