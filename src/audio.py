#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

import os
import hashlib
import pyaudio
from datetime import datetime, timedelta
import time
import gtts
import pyttsx3
import webrtcvad
import wave
import tinydb
import numpy as np
from array import array
from struct import pack
from subprocess import DEVNULL, Popen, PIPE, STDOUT
from collections import deque
import speech_recognition as sr
#from socketIO_client import SocketIO, BaseNamespace

#class StateNamespace(BaseNamespace):
#    pass

# setting
#engine_local = pyttsx3.init('sapi5');
#voices = engine_local.getProperty('voices')
#for voice in voices:
#    print(voice)
    #if voice.languages[0] == b'\x05es':
    #    engine_local.setProperty('voice', voice.id)
    #    break
tream= None
socket_state=None
audio=None
vad=None
Audio = tinydb.Query()

block_duration=10
padding_duration=1000
SAMPLERATE=48000
FRAMES_PER_BUFFER=SAMPLERATE*block_duration/1000
NUM_PADDING_CHUNKS=int(padding_duration/block_duration)
NUM_WINDOW_CHUNKS=int(400/block_duration)
ring_buffer=deque(maxlen=NUM_PADDING_CHUNKS)
ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
ring_buffer_index=0

AUDIOS=[]
SPEECHRECDIR=None
TTSDIR=None
TTS=None
ENGINE_LOCAL=None
DB=None
rec = sr.Recognizer()

# 0 - not connected
# 1 - connected
# 2 - listening silence
# 3 - listening voice
# 4 - stop listening
STATE={
    "main":0,
    "time_start_listening":None
}

def clear_audios():
    AUDIOS=[]

def tts(msg,lang="es-us"):
    if TTS==0:
        tts_local(msg,lang=lang)
    elif TTS==1:
        tts_google(msg,lang=lang)
    else:
        pass

def tts_local(msg,lang='es-us'):
    ENGINE_LOCAL.say(msg)
    ENGINE_LOCAL.runAndWait() ;

def tts_google(msg,lang=None):
    global DB
    hashing = hashlib.md5(msg.encode('utf-8')).hexdigest()
    if DB:
        res = DB.search((Audio.hash == hashing) & (Audio.type=='google'))
    else:
        res=[]
    if len(res)>0:
        mp3_filename=res[0]['mp3']
    else:
        mp3_filename=os.path.join(TTSDIR,f'{hashing}_google.mp3')
        tts = gtts.gTTS(msg,lang=lang if lang else TTS_LANG )
        tts.save(mp3_filename)
    p = Popen(['mpg321',mp3_filename], stdout=DEVNULL, stderr=STDOUT)
    p.communicate()
    assert p.returncode == 0
    if not DB is None:
        DB.insert({'hash':hashing,'type':'google','mp3':mp3_filename})

def vad_aggressiveness(a):
    vad.set_mode(a)

# Monitoring
def audio_devices():
    devices=[]
    for i in range(audio.get_device_count()):
        info=audio.get_device_info_by_index(i)
        devices.append('{0} -> {1}'.format(i,"\n".join(["   {0}:{1}".format(x, y) for x,y in info.items()])))

    return devices

def list_voices(engine=None):
    if engine=='local':
        engine = pyttsx3.init() 
        voices = engine.getProperty('voices')
        for voice in voices:
            print(voice)
    if engine=="google":
        langs=gtts.lang.tts_langs()
        for lang in langs:
            print(lang)

def enable_tts(engine=None,tts_dir=tts,db=None,voice='es',language='es-us'):
    global TTSDIR
    global TTS
    global DB
    global ENGINE_LOCAL
    TTSDIR=tts_dir
    if not DB:
        DB=db
    if engine=='local':
        TTS=0
        ENGINE_LOCAL = pyttsx3.init() 
        ENGINE_LOCAL.setProperty('voice', voice)
    elif engine=='google':
        TTS=1
        TTS_LANG=language
    else:
        TSS=None


def enable_audio_listening(device=None,samplerate=16000,block_duration=10,padding_duration=1000, 
        host=None, port=None, channels=1,aggressiveness=None,
        speech_recognition_dir="speech_recognition"):
    global socket_state
    global audio
    global vad
    global SPEECHRECDIR
    global SAMPLERATE
    audio = pyaudio.PyAudio()
    vad = webrtcvad.Vad()
    #vad.aggressiveness(aggressiveness)
    if host:
        socket = SocketIO(host,port)
        socket_state = socket.define(StateNamespace, '/state')

    SAMPLERATE=samplerate
    SPEECHRECDIR=speech_recognition_dir
    FRAMES_PER_BUFFER=int(samplerate*block_duration/1000)
    NUM_PADDING_CHUNKS=int(padding_duration/block_duration)
    NUM_WINDOW_CHUNKS=int(250/block_duration)
    ring_buffer=deque(maxlen=NUM_PADDING_CHUNKS)
    ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
    ring_buffer_index=0
    stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=samplerate,
            frames_per_buffer=FRAMES_PER_BUFFER,
            input=True,
            start=False,
            stream_callback=callback
        )
    stream.start_stream()
    STATE['main']="1"


voiced_buffer=np.array([],dtype='Int16')
ring_buffer=np.array([],dtype='Int16')
wave_file=None
filename_wav="tmp.wav"
# Audio capturing
def callback(in_data, frame_count, time_info, status):
    global ring_buffer_index, ring_buffer_flags,triggered, voiced_buffer, ring_buffer, wave_file, SPEECHRECDIR, filename_wav, STATE, socket_state, SAMPLERATE
    if socket_state:
        socket_state.emit('audio',STATE)
    if STATE['main']==1 or STATE['main']==4:
        ring_buffer_index=0
        voiced_buffer=np.array([],dtype='Int16')
        ring_buffer=np.array([],dtype='Int16')
        return (in_data,pyaudio.paContinue)
    is_speech = vad.is_speech(in_data, 16000)
    in_data_ = np.fromstring(in_data, dtype='Int16')
    in_data_ = in_data_/32767.0
    ring_buffer_flags[ring_buffer_index] = 1 if is_speech else 0
    ring_buffer_index += 1
    ring_buffer_index %= NUM_WINDOW_CHUNKS
    if STATE['main']==2:
        ring_buffer=np.concatenate((ring_buffer,in_data_))
        num_voiced = sum(ring_buffer_flags)
        if num_voiced > 0.5 * NUM_WINDOW_CHUNKS:
            STATE['main'] = 3
            filename_wav = os.path.join(SPEECHRECDIR,datetime.now().strftime("%Y%m%d_%H%M%S"))
            wave_file = wave.open(filename_wav, 'wb')
            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)
            wave_file.setframerate(SAMPLERATE)
            voiced_buffer=np.array(ring_buffer)
            ring_buffer=np.array([],dtype="Int16")
    else:
        voiced_buffer=np.concatenate((voiced_buffer,in_data_))
        num_unvoiced = NUM_WINDOW_CHUNKS - sum(ring_buffer_flags)
        if len(voiced_buffer)>0 and num_unvoiced > 0.90 * NUM_WINDOW_CHUNKS:
            STATE['main'] = 2
            if wave_file:
                in_data_ = np.int16(voiced_buffer*32767)
                wave_file.writeframes(in_data_.tostring())
                wave_file.close()
                AUDIOS.append((datetime.now(),filename_wav))
            voiced_buffer=np.array([],dtype="Int16")
    return (in_data,pyaudio.paContinue)

def pull_latest():
    now=datetime.now()
    while len(AUDIOS)==0 or AUDIOS[-1][0]+timedelta(milliseconds=400)<= now:
        return None
    return AUDIOS[-1][1]

def audio_state():
    return STATE

def start_listening():
    STATE['main']=2

def stop_listening():
    STATE['main']=4

def set_audio_dirname(dir):
    DIRAUDIOS=dir

def audio_close():
    if stream:
        stream.close()
    audio.terminate()

# Speech recogniser
def sr_google(filename):
    with sr.AudioFile(filename) as source:
        audio = rec.record(source)  # read the entire audio file

    # recognize speech using Google Speech Recognition
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
        # instead of `r.recognize_google(audio)`
        return rec.recognize_google(audio, language='es-mx')
    except sr.UnknownValueError:
        return 'UNK'
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))


