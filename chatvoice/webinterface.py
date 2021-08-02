#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

from aiohttp import web
import socketio
import sys
import os.path
import argparse
import threading


# local imports
import conversation
from audio import audio_connect, audio_devices, set_audio_dirname, vad_aggressiveness

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

async def index(request):
    with open('templates/index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


async def state(request):
    conv.start()
    with open('templates/state.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


@sio.on('connect', namespace='/state')
async def connect(sid, environ):
    conv.set_sid(sid)


@sio.on('say', namespace='/state')
async def message(sid, data):
    await sio.emit('turn log', data , namespace="/state")

@sio.on('input', namespace='/state')
async def message(sid, data):
    await sio.emit('turn log', data , namespace="/state")



@sio.on('audio', namespace='/state')
async def message(sid, data):
    await sio.emit('audio log', data , namespace="/state")


@sio.on('disconnect', namespace='/state')
def disconnect(sid):
    print('disconnect ', sid)


app.router.add_static('/static', 'static')
app.router.add_get('/', index)
app.router.add_get('/state', state)

# Main function
if __name__ == '__main__':
    p = argparse.ArgumentParser("webinterface")
    p.add_argument("CONV",
                    help="Conversation file")
    p.add_argument("--list_devices",
                    action="store_true", dest="list_devices",
                    help="List audio devices")
    p.add_argument("--rec_voice",
                    action="store_true", dest="rec_voice",
                    help="Activate voice recognition")
    p.add_argument("--audio_dir",default="rec_voice_audios",
                    action="store", dest="audio_dir",
                    help="Directory for audios for speech recognition")
    p.add_argument("--google_tts",
                    action="store_true", dest="google_tts",
                    help="Use google tts")
    p.add_argument("--local_tts",
                    action="store_true", dest="local_tts",
                    help="Use espeak local tts")
    p.add_argument("--samplerate",type=int,default=16000,
                    action="store", dest="samplerate",
                    help="Samplerate")
    p.add_argument("--channels",type=int,default=1,
            action="store", dest="channels",
            help="Number of channels microphone (1|2|...)")
    p.add_argument("--device",type=int,default=None,
                    action="store", dest="device",
                    help="Device number to connect audio")
    p.add_argument("--aggressiveness",type=int,default=None,
                    action="store", dest="aggressiveness",
                    help="VAD aggressiveness")
    p.add_argument("--host", default="127.0.0.1",
                   action="store", dest="host",
                   help="Root url [127.0.0.1]")
    p.add_argument("--port", default=5000, type=int,
                   action="store", dest="port",
                   help="Port url [500]")
    p.add_argument("-v", "--verbose",
                   action="store_true", dest="verbose",
                   help="Verbose mode [Off]")


    args = p.parse_args()


    if args.list_devices:
        for info in audio_devices():
            print(info)
        sys.exit()


    if args.google_tts:
        tts="google"
    elif args.local_tts:
        tts="local"
    else:
        tts=None

    # speech
    if not os.path.exists(os.path.join(os.getcwd(), args.audio_dir)):
        os.mkdir(os.path.join(os.getcwd(), args.audio_dir))

    set_audio_dirname(args.audio_dir)

    if args.aggressiveness:
        vad_aggressiveness(args.aggressiveness)
    conv = conversation.Conversation(
            filename=args.CONV,
            verbose=args.verbose,
            tts=tts,
            samplerate=args.samplerate,
            device=args.device,
            rec_voice=args.rec_voice,
            host=args.host,
            port=args.port
            )
    t = threading.Thread(target=conv.execute)
    conv.set_thread(t)

    web.run_app(app,
                host=args.host,
                port=args.port)
