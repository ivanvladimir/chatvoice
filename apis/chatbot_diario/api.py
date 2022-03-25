from typing import Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel


class Info(BaseModel):
    msg: str


app = FastAPI()


@app.post("/analyis")
def echo(info: Info):
    return {"msg": info.msg}


@app.post("/sentiments")
def echo(info: Info):
    # Hacer el analis de sentiminetos
    return {"msg": info.msg}


@app.post("/events")
def echo(info: Info):
    return {"msg": info.msg}
