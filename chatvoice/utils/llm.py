from ..core.config import LLMProvider, LLMSettings, Settings

llm_client = None


def init_llm_client(settings: Settings):
    if not isinstance(settings, LLMSettings):
        pass

    if settings.LLM_PROVIDER == LLMProvider.GOOGLE:
        from google import genai

        API_KEY = settings.get_key()
        llm_client = ("google", genai.Client(api_key=API_KEY))
        return llm_client


def llm_client_response(llm_client: tuple = ("none", None), input: str = ""):
    t, llm_client = llm_client
    if not len(input):
        return ""
    if not llm_client:
        return ""
    if t == "google":
        try:
            interaction = llm_client.interactions.create(
                model="gemini-3.1-flash-lite", input=input, store=False
            )
        except:
            interaction = None
        if interaction:
            return interaction.output_text
        else:
            return "mmm ..."


def get_llm_client():
    return llm_client
