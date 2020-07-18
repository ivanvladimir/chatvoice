import socketio
from conversation import Conversation, CONVERSATIONS
import threading
import os
from aiohttp import web
import uuid

from templates import *

conversations={}
config={}
sio = socketio.AsyncServer()

# SOCKET communication
@sio.on('connect', namespace='/cv')
async def connect(sid, environ):
    print("Connected",sid)

@sio.on('start', namespace='/cv')
async def start(sid,vals):
    conversation=CONVERSATIONS[vals['idd']]
    conversation.start()
    print("start")

@sio.on('say', namespace='/cv')
async def say(sid, data):
    print("say", data)
    await sio.emit('say log', data , namespace="/cv")

@sio.on('input finish', namespace='/cv')
async def input_finish(sid, data):
    conversation=CONVERSATIONS[data['idd']]
    conversation.input=data['message']
    print("input finish",data['message'])

@sio.on('input', namespace='/cv')
async def input(sid):
    print("input ->")
    await sio.emit('input start', namespace="/cv")

@sio.on('audio', namespace='/cv')
async def audio(sid, data):
    print("audio")
    await sio.emit('audio log', data , namespace="/cv")

@sio.on('disconnect', namespace='/cv')
def disconnect(sid):
    print('disconnect ', sid)

# Webpage behaviour
async def index(request):
    conversations_dir=config.get('conversations_path','conversations')
    options=[]
    for directory in os.listdir(os.path.join(conversations_dir)):
        main_path=os.path.join(conversations_dir,directory,'main.yaml')
        if os.path.isdir(os.path.join(conversations_dir,directory)) and os.path.exists(main_path):
            options.append((directory,main_path))

    rows=[]
    for conversation,path in options:
        rows.append(ROW_TABLE_CONVERSATION.format(path,conversation))

    table_conversation=TABLE_CONVERSATION.format("".join(rows))

    page=INDEX.format(table_conversation)
    return web.Response(text=page, content_type='text/html')

async def conversation(request):
    conv=request.match_info['conversation']
    conversations_dir=config.get('conversations_path','conversations')
    conv_file=os.path.join(conversations_dir,conv,'main.yaml')

    client = socketio.Client()

    conversation = Conversation(
        filename=conv_file,
        client=client,
        **config)
    t = threading.Thread(target=conversation.execute)
    conversation.set_thread(t)
    idd=str(uuid.uuid4())
    conversation.set_idd(idd)
    CONVERSATIONS[idd]=conversation
    page=CONVERSATION.replace("IDD",idd)
    return web.Response(text=page, content_type='text/html')

def start_server(config_):
    global config 
    config=config_
    app = web.Application()
    sio.attach(app)
    app.router.add_get('/', index)
    app.router.add_get('/execute/{conversation}', conversation)
    return web, app



