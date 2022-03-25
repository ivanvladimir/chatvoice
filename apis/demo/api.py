from typing import Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel


class Info(BaseModel):
    msg: str


app = FastAPI()


@app.get("/msg")
def msg():
    return {"msg": "This mesg comes from an api"}


@app.post("/echo")
def echo(info: Info):
    return {"msg": info.msg}
