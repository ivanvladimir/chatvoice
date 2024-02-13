import openai

def init_chatgpt(key):
    openai.api_key = key

def generate_response(messages,engine="text-davinci-003",temperature=0.5,max_tokens=1024):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        )
