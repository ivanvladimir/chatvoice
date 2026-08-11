from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

from ..core.config import LLMProvider, LLMSettings, Settings

llm_client = None


class StructureResponse(BaseModel):
    status: Dict = Field(
        description="A dictionary containing the information to store in slots"
    )


def _history_to_steps(history: list) -> list[dict]:
    """
    Convert per-session history entries (`{"role": "user"|"assistant", "text": str}`,
    as recorded by cmd_say/cmd_listen) into the google-genai `input` step format
    (`UserInputStep`/`ModelOutputStep`, each carrying a text `Content` block).
    """
    steps = []
    for turn in history:
        text = turn.get("text")
        if not text:
            continue
        step_type = "user_input" if turn.get("role") == "user" else "model_output"
        steps.append({"type": step_type, "content": [{"type": "text", "text": text}]})
    return steps


def init_llm_client(settings: Settings):
    if not isinstance(settings, LLMSettings):
        pass

    if settings.LLM_PROVIDER == LLMProvider.GOOGLE:
        from google import genai

        API_KEY = settings.get_key()
        llm_client = ("google", genai.Client(api_key=API_KEY))
        return llm_client


def llm_client_response(
    llm_client: tuple = ("none", None),
    input: Union[str, list] = "",
    structured: bool = False,
    history: Optional[list] = None,
):
    """
    Send a prompt to the configured LLM client.

    `input` is either a plain string (a single user prompt, no system
    instruction) or a `[system, user]` pair -- either element may be None --
    as produced by the structured `llm:` command form.

    `history` is the session's prior conversation turns (as recorded by
    cmd_say/cmd_listen, see ctx['history']): a list of `{"role": "user" |
    "assistant", "text": str}` dicts, oldest first. When given, they're sent
    ahead of the current user turn as a multi-turn `input` instead of a bare
    string, so the model sees the conversation so far.
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
        request_input: Any = user
        if history:
            request_input = _history_to_steps(history) + [
                {"type": "user_input", "content": [{"type": "text", "text": user}]}
            ]

        kwargs = {
            "model": "gemini-3.1-flash-lite",
            "input": request_input,
            "store": False,
        }
        if system:
            kwargs["system_instruction"] = system
        if structured:
            kwargs["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": StructureResponse.model_json_schema(),
            }

        try:
            interaction = llm_client.interactions.create(**kwargs)
        except Exception as e:
            print(e)
            interaction = None
        if interaction:
            print(">>>>",interaction.output_text)
            if structured:
                response = StructureResponse.model_validate_json(
                    interaction.output_text
                )
                return response.model_dump()
            else:
                return interaction.output_text
        else:
            return {}


def get_llm_client():
    return llm_client
