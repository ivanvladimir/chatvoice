import openai

def init_chatgpt(key):
    openai.api_key = key

def generate(prompt,engine="text-davinci-003",temperature=0.5,max_tokens=1024):
    return  openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=max_tokens,
            n=3,
            stop=None,
            temperature=temperature,
        )

