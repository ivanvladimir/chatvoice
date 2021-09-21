# Mini fastapi example app.
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Request
import time

class Arguments(BaseModel):
    model: str = "__DEFAULT__"
    title: str = "las golondrinas"
    firstlines: Optional[str] = None
    max_length: int = 150
    min_length: int = 50
    num_beams: Optional[int] =None
    top_k: Optional[int] = None
    top_p: Optional[float]  = None
    do_sample: bool = True
    early_stopping: bool = True
    no_repeat_ngram_size: Optional[int] = None
    num_return_sequences: Optional[int] = None
    temperature: Optional[float] = None
    seed: Optional[int] = None


app = FastAPI()

@app.get("/")
def main():
    #  Time
    start_time = time.time()
    elapsed_time = lambda: time.time() - start_time
    # Recovering parameters from ULR
    return {'elapsed_time': f'{elapsed_time():2.3f}'}

