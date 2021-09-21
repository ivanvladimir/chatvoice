# Mini fastapi example app.
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import time
import os

def create_app():
    from .config import get_config
    config=dict(get_config())
    app = FastAPI()
    app.mount("/static", StaticFiles(directory="static"),  name="static")
    templates = Jinja2Templates(directory="templates")

    @app.get("/",response_class=HTMLResponse)
    async def start(request: Request):
        start_time = time.time()
        conversations_dir=config.get('conversations_dir','conversations')
        options=[]
        for directory in os.listdir(os.path.join(conversations_dir)):
            main_path=os.path.join(conversations_dir,directory,'main.yaml')
            if os.path.isdir(os.path.join(conversations_dir,directory)) and os.path.exists(main_path):
                options.append((directory,main_path))


        elapsed_time = lambda: time.time() - start_time
        return templates.TemplateResponse(
                "index.html",
                {"options": options,
                    "request": request})

    return app
