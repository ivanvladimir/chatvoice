from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_CHATGPT_KEY: str = "USE_THIS_VARIABLE_TO_SPECIFY_YOUR_KEY_DO_IT_IN_THE_FILE"
    API_CHATGPT_URL_PREFIX: str = "/chatgpt"
    API_CHATGPT_ORGANIZATION: str = ""
    API_CHATGPT_PROJECT: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
