from openai import OpenAI
from pydantic import BaseModel

class TagEvent(BaseModel):
    tag: str

def init_chatgpt(organization, project):
    return OpenAI(
            organization=organization,
            project=project)

def generate_response(client,messages,model="gpt-4o-mini",temperature=None,max_tokens=None,seed=1337):
    completion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            messages=messages)
    return completion


def generate_structured(client,messages,model="gpt-4o-mini-2024-07-18",temperature=None,max_tokens=None,seed=1337):
    completion = client.beta.chat.completions.parse(
            model=model,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            messages=messages,
            response_format=TagEvent)
    return completion

def moderation(client, text):
    return client.moderations.create(input=text)
