from typing import Optional, Union

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


def llm_client_response(
    llm_client: tuple = ("none", None), input: Union[str, list] = ""
):
    """
    Send a prompt to the configured LLM client.

    `input` is either a plain string (a single user prompt, no system
    instruction) or a `[system, user]` pair -- either element may be None --
    as produced by the structured `llm:` command form.
    """
    t, llm_client = llm_client

    system: Optional[str]
    if isinstance(input, (list, tuple)):
        system, user = (list(input) + [None, None])[:2]
    else:
        system, user = None, input

    if not user:
        return ""
    if not llm_client:
        return ""
    if t == "google":
        kwargs = {"model": "gemini-3.1-flash-lite", "input": user, "store": False}
        if system:
            kwargs["system_instruction"] = system

        try:
            interaction = llm_client.interactions.create(**kwargs)
        except Exception as e:
            print(e)
            interaction = None
        if interaction:
            return interaction.output_text
        else:
            return "mmm ..."


def get_llm_client():
    return llm_client
