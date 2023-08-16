# Main webservice
from fastapi import FastAPI, Request, Depends, Form
from typing_extensions import Annotated
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Any

from sqlalchemy.orm import Session

import arrow
import time
import datetime
import os
import json
from .conversation import Conversation
import uuid
import sqlite3

def create_app():
    from .config import get_config
    from . import crud, models, schemas
    from .database import SessionLocal, engine
    START_TIME = arrow.utcnow()
    STATUS = "active"
    NAME = "chatvoice"

    models.Base.metadata.create_all(bind=engine)

    config = dict(get_config())

    prefix_url=config.get('prefix_url','/')
    prefix_ws=config.get('prefix_ws','/ws/')
    host=config.get('host','0.0.0.0')
    port=config.get('port','5000')
    port_ws=config.get('port_ws','5000')
    protocol_ws=config.get('protocol_ws','ws')
    server_ws=config.get('server_ws','0.0.0.0')
    login=config.get('login',False)
    app = FastAPI()
    app.mount(prefix_url+"static", StaticFiles(directory=config.get("static","static")), name="static")
    templates = Jinja2Templates(directory=config.get("templates","templates"))
    elapsed_time = lambda s: f"{time.time() - s:0.2}s"
    CONVERSATIONS = {}
    CLIENTS = {}

    # Dependency
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_new_conversation(chat, client_id):
        import threading

        config = dict(get_config())
        conversation = Conversation(
            filename=os.path.join(
                config.get("conversations_dir", "conversations"), chat, "main.yaml"
            ),
            client_id=client_id,
            **config,
        )
        t = threading.Thread(target=conversation.execute)
        conversation.set_thread(t)
        conversation.set_idd(client_id)
        # audio.enable_server(client)
        return conversation

    ## Status page
    @app.get(prefix_url+"status", response_class=JSONResponse)
    async def status(request: Request):
        """Prints status of API"""
        start_time = time.time()
        diff = arrow.utcnow() - START_TIME
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return JSONResponse(content={
            "NAME": NAME,
            "status": STATUS,
            "uptime": f"Elapsed Time: {days} Days, {hours} Hours, {minutes} Minutes, {seconds} Seconds.",
        })

    ## Main page
    if config.get('index','True')=='True':
        @app.get(prefix_url, response_class=HTMLResponse)
        async def index(request: Request):
            start_time = time.time()
            conversations_dir = config.get("conversations_dir", "conversations")
            options = []
            for directory in os.listdir(os.path.join(conversations_dir)):
                main_path = os.path.join(conversations_dir, directory, "main.yaml")
                if os.path.isdir(
                    os.path.join(conversations_dir, directory)
                ) and os.path.exists(main_path):
                    options.append((directory, main_path))

            return templates.TemplateResponse(
                "index.html",
                {
                    "options": options,
                    "request": request,
                    "elapsed_time": elapsed_time(start_time),
                },
            )

    if not config.get('entry_point',False):
        if not config.get('login',False):
            @app.get(prefix_url+"execute/{name}", response_class=HTMLResponse)
            async def execute(name: str, request: Request):
                start_time = time.time()
                return templates.TemplateResponse(
                    "conversation.html",
                    {
                        "request": request,
                        "chat_name": name,
                        "elapsed_time": elapsed_time(start_time),
                        "prefix": prefix_ws,
                        "protocol": protocol_ws,
                        "server":server_ws,
                        "port":port_ws,
                    },
                )
        else:
            @app.get(prefix_url+"execute/{name}", response_class=HTMLResponse)
            async def login(name: str, request: Request, db: Session = Depends(get_db)):
                start_time = time.time()
                return templates.TemplateResponse(
                    "login.html",
                    {
                        "request": request,
                        "chat_name": name,
                        "elapsed_time": elapsed_time(start_time),
                    },
                )

            @app.post(prefix_url+"execute/{name}/{uniqueID}", response_class=HTMLResponse)
            async def execute(uniqueId: int, request: Request, db: Session = Depends(get_db)):
                start_time = time.time()
                da = await request.form()
                da = jsonable_encoder(da)
                return templates.TemplateResponse(
                    "conversation.html",
                    {
                        "chat_name": name,
                        "elapsed_time": elapsed_time(start_time),
                        "prefix": prefix_ws,
                        "protocol": protocol_ws,
                        "server":server_ws,
                        "port":port_ws,
                    },
                )

    else:
        if not config.get('login',False):
            @app.get(prefix_url+f"{config.get('entry_point')}", response_class=HTMLResponse)
            async def execute(request: Request):
                start_time = time.time()
                return templates.TemplateResponse(
                    "conversation.html",
                    {
                        "request": request,
                        "chat_name": config.get('entry_point'),
                        "elapsed_time": elapsed_time(start_time),
                        "prefix": prefix_ws,
                        "protocol": protocol_ws,
                        "server":server_ws,
                        "port":port_ws,
                    },
                )
        else:
            @app.get(prefix_url+f"{config.get('entry_point')}", response_class=HTMLResponse)
            async def login( request: Request, db: Session = Depends(get_db)):
                start_time = time.time()
                return templates.TemplateResponse(
                    "login.html",
                    {
                        "request": request,
                        "chat_name": config.get('entry_point'),
                        "elapsed_time": elapsed_time(start_time),
                    },
                )

            @app.post(prefix_url+f"{config.get('entry_point')}"+"/{uniqueId}", response_class=HTMLResponse)
            async def execute(uniqueId: int, request: Request, db: Session = Depends(get_db)):
                start_time = time.time()
                da = await request.form()
                da = jsonable_encoder(da)
                user=crud.get_user_by_identifier(db,uniqueId)
                if not user:
                    user=schemas.UserCreate(identifier=uniqueId,data=json.dumps(da))
                    crud.create_user(db,user)
                else:
                    user.data=json.dumps(da)
                    db.commit()

                return templates.TemplateResponse(
                    "conversation.html",
                    {
                        "request": request,
                        "chat_name": config.get('entry_point'),
                        "elapsed_time": elapsed_time(start_time),
                        "prefix": prefix_ws,
                        "protocol": protocol_ws,
                        "server": server_ws,
                        "port": port_ws,
                        "data": da
                    },
                )

    ## Websocket
    class ConnectionManager:
        def __init__(self):
            self.connections: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            try:
                self.connections.remove(websocket)
            except ValueError:
                pass

        async def send_personal_message(self, message: str, websocket: WebSocket):
            await websocket.send_text(message)

        async def broadcast(self, data: str):
            for connection in self.connections:
                await connection.send_text(data)

    manager = ConnectionManager()

    @app.websocket(prefix_ws+"{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: int):
        await manager.connect(websocket)
        CLIENTS[client_id] = websocket
        try:
            while True:
                data_ = await websocket.receive_text()
                data = json.loads(data_)
                if data["cmd"] == "start":
                    preferences=data['data']
                    conversation = CONVERSATIONS.get(client_id, None)
                    if conversation is None:
                        conversation = create_new_conversation(
                            data["conversation"], client_id
                        )
                        conversation.set_webclient_sid(client_id)
                        CONVERSATIONS[client_id] = conversation
                        conversation.start()
                    # Initializating slots for conversation
                    for k,v in preferences.items():
                        conversation.slots[k]=v
                    continue
                if data["cmd"] == "say":
                    client_id = data["client_id"]
                    w2 = CLIENTS[client_id]
                    await w2.send_text(data_)
                    continue
                if data["cmd"] == "finish":
                    client_id = data["client_id"]
                    w2 = CLIENTS[client_id]
                    await w2.send_text(data_)
                    continue
                if data["cmd"] == "activate input":
                    client_id = data["client_id"]
                    w2 = CLIENTS[client_id]
                    await w2.send_text(data_)
                    continue
                if data["cmd"] == "input completed":
                    conversation = CONVERSATIONS.get(client_id, None)
                    conversation.input = data["msg"]
                    continue
        except WebSocketDisconnect:
            try:
                c2 = CONVERSATIONS[client_id]
                c2.EXIT_()
                CONVERSATIONS.pop(client_id)
                manager.disconnect(c2)
            except KeyError:
                pass
            try:
                del CLIENTS[client_id]
            except KeyError:
                pass

    return app
