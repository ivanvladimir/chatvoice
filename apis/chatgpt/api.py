# Creadores: Karim Acosta, Ivan Meza

from typing import (Optional, List)
from fastapi import FastAPI, Request
from pydantic import BaseModel
from functools import lru_cache
from ml_model import init_chatgpt, generate_response, moderation, generate_structured

import arrow
import os

__VERSION__ = "0.0.2"
__API_NAME__ = "ChatGPTt API"

app = FastAPI()

class GenerateResponseOptions(BaseModel):
    """Prompt to generate from

    Aguments:
        messages   Text with history of prompts
    """
    messages: List[dict]


class ModerateText(BaseModel):
    """Text to moderate

    Aguments:
        text   Text to moderate
    """
    text: str


def create_app(test_config=None):
    START_TIME = arrow.utcnow()
    STATUS = "active"
    NUM_RESPONSES=0
    PROMPT_TOKENS=0
    COMPLETION_TOKENS=0

    # Arrange configuration
    import config

    @lru_cache()
    def get_settings():
        return config.Settings()

    def elapsed_time(start_time):
        '''Calculates the elapsed time'''
        return (arrow.utcnow() - start_time).total_seconds()

    settings = get_settings()
    client = init_chatgpt(
            organization=settings.API_CHATGPT_ORGANIZATION,
            project=settings.API_CHATGPT_PROJECT)

    app = FastAPI()
    api_ = FastAPI()

    @api_.get("/status")
    def status():
        """Prints status of API"""
        diff = arrow.utcnow() - START_TIME
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return {
            "name": __API_NAME__,
            "version": __VERSION__,
            "status": STATUS,
            "uptime": f"Elapsed Time: {days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds.",
        }

    @api_.post("/generate_response")
    def generate_response_(info: GenerateResponseOptions):
        start_time = arrow.utcnow()
        completion= generate_response(
                client,
                info.messages
                )
        response=completion.choices[0].message.content
        #NUM_RESPONSES+=1
        #PROMPT_TOKENS+=completion['usage']['prompt_tokens']
        #COMPLETION_TOKENS+=completion['usage']['completion_tokens']

        print(response)

        return {
            "messages": info.messages,
            "response": response,
            "elapsed_time": f"{elapsed_time(start_time):2.4f} segs",
        }


    @api_.post("/generate_structured")
    def generate_structured_(info: GenerateResponseOptions):
        start_time = arrow.utcnow()
        completion= generate_structured(
                client,
                info.messages
                )
        response=completion.choices[0].message.parsed
        #NUM_RESPONSES+=1
        #PROMPT_TOKENS+=completion['usage']['prompt_tokens']
        #COMPLETION_TOKENS+=completion['usage']['completion_tokens']

        print(response.tag)

        return {
            "messages": info.messages,
            "response": response.tag,
            "elapsed_time": f"{elapsed_time(start_time):2.4f} segs",
        }

    @api_.post("/moderate")
    def moderation_(info: ModerateText):
        start_time = arrow.utcnow()
        moderation= (
                client,
                info.text
                )
        categories=[]
        for k,v in moderation['results']['categories']:
            if v:
                categories.append(k)
        
        return {
            "flagged":moderation['results']['flagged'],
            "categories": categories,
            "elapsed_time": f"{elapsed_time(start_time):2.4f} segs",
        }

    app.mount(f"/{settings.API_CHATGPT_URL_PREFIX}", api_)
    return app



app = create_app()
