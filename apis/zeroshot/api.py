from typing import (Optional, List)
from fastapi import FastAPI, Request
from pydantic import BaseModel
from functools import lru_cache
from ml_model import init_transformer, classify_transformer

import arrow
import os

__VERSION__ = "0.0.1"
__API_NAME__ = "Zeroshot Text API"

app = FastAPI()


class PreprocessTextOptions(BaseModel):
    """Options to configure the pre-processing of text

    Options:
        use_lower   Lower the tweet

    """

    use_lower: Optional[bool] = False


class TextOptions(PreprocessTextOptions):
    """Arguments and options for text classification

    Aguments:
        text   Text to classify
    """

    text: str
    labels: List[str]
    template: str = "Es ejemplo de {}"


def create_app(test_config=None):
    START_TIME = arrow.utcnow()
    STATUS = "active"

    # Arrange configuration
    import config

    @lru_cache()
    def get_settings():
        return config.Settings()

    def elapsed_time(start_time):
        '''Calculates the elapsed time'''
        return (arrow.utcnow() - start_time).total_seconds()

    settings = get_settings()

    model_ = init_transformer(settings.API_ZEROSHOT_MODEL_NAME)

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
            "model": settings.API_ZEROSHOT_MODEL_NAME,
            "model_loaded": True if model_ else False,
            "status": STATUS,
            "uptime": f"Elapsed Time: {days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds.",
        }

    @api_.post("/classify")
    def classify(info: TextOptions):
        start_time = arrow.utcnow()
        res, (text_, labels_, template_) = classify_transformer(info.text, 
                info.labels,
                info.template,
                use_lower=info.use_lower)

        return {
            "text": info.text,
            "text_": text_,
            "labels_": labels_,
            "template_": template_,
            "result": res,
            "elapsed_time": f"{elapsed_time(start_time):2.4f} segs",
        }

    app.mount(f"/{settings.API_ZEROSHOT_URL_PREFIX}", api_)
    return app


app = create_app()