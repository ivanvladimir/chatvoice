# Mini fastapi example app.
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import time
import os
import json
from .conversation import Conversation


def create_app():
    from .config import get_config

    config = dict(get_config())
    prefix_url=config.get('prefix_url','/')
    prefix_ws=config.get('prefix_ws','/ws/')
    host=config.get('host','0.0.0.0')
    port=config.get('port','5000')
    port_ws=config.get('port_ws','5000')
    protocol_ws=config.get('protocol_ws','ws')
    server_ws=config.get('server_ws','0.0.0.0')
    app = FastAPI()
    app.mount(prefix_url+"static", StaticFiles(directory=config.get("static","static")), name="static")
    templates = Jinja2Templates(directory=config.get("templates","templates"))
    elapsed_time = lambda s: f"{time.time() - s:0.2}s"
    CONVERSATIONS = {}
    CLIENTS = {}

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

    ## Main page
    if config.get('index','True')=='True':
        @app.get(prefix_url, response_class=HTMLResponse)
        async def list_conversations(request: Request):
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
                    "port":port_ws
                },
            )
    else:
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
                    "port":port_ws
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
                    conversation = CONVERSATIONS.get(client_id, None)
                    if conversation is None:
                        conversation = create_new_conversation(
                            data["conversation"], client_id
                        )
                        conversation.set_webclient_sid(client_id)
                        CONVERSATIONS[client_id] = conversation
                        conversation.start()
                if data["cmd"] == "say":
                    client_id = data["client_id"]
                    w2 = CLIENTS[client_id]
                    await w2.send_text(data_)
                if data["cmd"] == "activate input":
                    client_id = data["client_id"]
                    w2 = CLIENTS[client_id]
                    await w2.send_text(data_)
                if data["cmd"] == "input completed":
                    conversation = CONVERSATIONS.get(client_id, None)
                    conversation.input = data["msg"]
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
