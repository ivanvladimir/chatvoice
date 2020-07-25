import socketio
from conversation import Conversation, CONVERSATIONS
import threading
import os
from aiohttp import web
import uuid

from templates import *
import audio

CONVERSATIONS={}
CLIENTS={}
config={}
sio = socketio.AsyncServer()
def create_new_conversation(idd):
    client,conv_file,extra_config=CLIENTS[idd]
    config_=dict(config)
    config_.update(extra_config)
    conversation = Conversation(
        filename=conv_file,
        client=client,
        **config_)
    t = threading.Thread(target=conversation.execute)
    conversation.set_thread(t)
    conversation.set_idd(idd)
    CONVERSATIONS[idd]=conversation
    audio.enable_server(client)
    return conversation

# SOCKET communication
@sio.on('connect', namespace='/cv')
async def connect(sid, environ):
    print("Connected",sid)

@sio.on('start', namespace='/cv')
async def start(sid,vals):
    conversation=CONVERSATIONS.get(vals['idd'],None)
    if conversation is None:
        conversation=create_new_conversation(vals['idd'])
    conversation.set_webclient_sid(sid)
    conversation.start()
    print("start")

@sio.on('finished', namespace='/cv')
async def finished(sid,vals):
    del CONVERSATIONS[vals['idd']]
    client,_,_=CLIENTS[vals['idd']]
    await sio.emit('finished log',{}, namespace="/cv",room=vals['webclient_sid'])
    client.disconnect()
    print("start")

@sio.on('say', namespace='/cv')
async def say(sid, data):
    print("say", data)
    await sio.emit('say log', data , namespace="/cv",room=data['webclient_sid'])

@sio.on('input finish', namespace='/cv')
async def input_finish(sid, data):
    conversation=CONVERSATIONS[data['idd']]
    conversation.input=data['message']
    print("input finish",data['message'])

@sio.on('input', namespace='/cv')
async def input(sid,data):
    print("input ->")
    await sio.emit('input start', namespace="/cv",room=data['webclient_sid'])

@sio.on('input log', namespace='/cv')
async def input(sid,data):
    print("input ->")
    await sio.emit('input log', data, namespace="/cv",room=data['webclient_sid'])

@sio.on('audio', namespace='/cv')
async def audio_(sid, data):
    await sio.emit('audio log', data , namespace="/cv")

@sio.on('get_state', namespace='/cv')
async def input(sid,data):
    print("get_state ->")
    await sio.emit('state log', {'speech_available':not audio.SPEECHREC, 'tts_avialable': True if audio.TTS is None else True }, namespace="/cv",room=sid)

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
    for ii,(conversation,path) in enumerate(options):
        rows.append(ROW_TABLE_CONVERSATION.format(path,conversation,ii))

    table_conversation=TABLE_CONVERSATION.format("".join(rows))

    page=INDEX.replace('TABLE',table_conversation)
    page=page.replace('TOTAL_CONVERSATIONS',str(len(options)))
    return web.Response(text=page, content_type='text/html')

async def conversation(request):
    conv=request.match_info['conversation']
    conversations_dir=config.get('conversations_path','conversations')
    conv_file=os.path.join(conversations_dir,conv,'main.yaml')
    extra_config={}
    if request.query.get('asr',False):
        extra_config['speech_recognition']=True
    if request.query.get('tts',False):
        extra_config['tts']=request.query['tts']

    client = socketio.Client()
    idd=str(uuid.uuid4())
    CLIENTS[idd]=(client,conv_file,extra_config)
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



