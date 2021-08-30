#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0
import faulthandler; faulthandler.enable()
import os
import queue
import hashlib
from datetime import datetime, timedelta
import time
# Loading audio libraries
import sounddevice as sd # Listening
import wave 
import gtts # TTS google
import pyttsx3 # TTS local
import webrtcvad # VAD
import speech_recognition as sr # Speech recognition
from playsound import playsound # reproducing mp3
import tinydb
import numpy as np
from array import array
from struct import pack
from subprocess import DEVNULL, Popen, PIPE, STDOUT
from collections import deque
#import socketio

stream= None
client=None
audio=None
vad=None
Audio = tinydb.Query()

block_duration=10
padding_duration=1000
SAMPLERATE=48000
FRAMES_PER_BUFFER=SAMPLERATE*block_duration/1000
NUM_PADDING_CHUNKS=int(padding_duration/block_duration)
NUM_WINDOW_CHUNKS=int(600/block_duration)
ring_buffer=deque(maxlen=NUM_WINDOW_CHUNKS)
q=queue.Queue()
ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
ring_buffer_index=0

AUDIOS=[]
SPEECHRECDIR=None
SPEECHREC=False
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
    """Removes audios from history"""
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
    """ TTS from google, ask for mp3 and reproduces it; if in database recovers it and play it"""
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
    playsound(mp3_filename)
    if not DB is None:
        DB.insert({'hash':hashing,'type':'google','mp3':mp3_filename})

def vad_aggressiveness(a):
    """Sets the aggressiveness of the VAD"""
    vad.set_mode(a)

# Monitoring
def audio_devices():
    return sd.query_devices()

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

def enable_server(client_):
    global client
    client = client_

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
        TTS=None


def enable_audio_listening(device=None,samplerate=16000,block_duration=10,padding_duration=1000, 
        host=None, port=None, channels=1,aggressiveness=None,
        speech_recognition_dir="speech_recognition"):
    global client, audio, vad, SPEECHRECDIR, SAMPLERATE, SPEECHREC, NUM_WINDOW_CHUNKS, NUM_WINDOW_CHUNKS
    vad = webrtcvad.Vad()
    #vad.aggressiveness(aggressiveness)

    SAMPLERATE=samplerate
    SPEECHRECDIR=speech_recognition_dir
    FRAMES_PER_BUFFER=int(samplerate*block_duration/1000)
    NUM_PADDING_CHUNKS=int(padding_duration/block_duration)
    NUM_WINDOW_CHUNKS=int(250/block_duration)

    stream=sd.InputStream(samplerate=SAMPLERATE,
            blocksize=FRAMES_PER_BUFFER,
            channels=channels,
            device=device,
            callback=callback)
    stream.start()
    SPEECHREC=True

voiced_buffer=np.array([],dtype='float16')
ring_buffer=deque(maxlen=NUM_WINDOW_CHUNKS)
q=queue.Queue()
ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
ring_buffer_index=0
sound_file=None
filename_wav="tmp.wav"
# Audio capturing
def callback(indata__, frames, time, status):
    global ring_buffer_index, ring_buffer_flags,triggered, voiced_buffer, ring_buffer, sound_file, SPEECHRECDIR, filename_wav, STATE, client, SAMPLERATE, q
    if status:
        print(status, file=sys.stderr)

    q.put(indata__.copy())
    #if client:
    #    client.emit('audio',STATE,namespace='/cv')
    print(STATE['main'])
    if STATE['main']==1 or STATE['main']==4:
        if ring_buffer_index==0:
            return None
        ring_buffer_index=0
        voiced_buffer=np.array([],dtype='float16')
        ring_buffer=deque(maxlen=NUM_WINDOW_CHUNKS)
        ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
        return None
    indata=q.get()
    audio_data_one = indata[::1, 0] # Only one channel to save
    audio_data = map(lambda x: (x+1)/2 , audio_data_one)
    audio_data = np.fromiter(audio_data, np.float16)
    is_speech = vad.is_speech(audio_data.tobytes(), SAMPLERATE)
    ring_buffer_flags[ring_buffer_index] = 1 if is_speech else 0
    ring_buffer_index += 1
    ring_buffer_index %= NUM_WINDOW_CHUNKS
    if STATE['main']==2:
        num_voiced = sum(ring_buffer_flags)
        ring_buffer.append(audio_data_one)
        if num_voiced > 0.5 * NUM_WINDOW_CHUNKS:
            STATE['main'] = 3
            filename_wav = os.path.join(SPEECHRECDIR,f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav')
            sound_file = wave.open(filename_wav, 'wb')
            sound_file.setnchannels(1)
            sound_file.setsampwidth(2)
            sound_file.setframerate(SAMPLERATE)
            for audio_data_one in ring_buffer:
                in_data_ = np.int16(audio_data_one*32767)
                sound_file.writeframes(in_data_.tostring())
    else:
        # STATE 3
        num_unvoiced = NUM_WINDOW_CHUNKS - sum(ring_buffer_flags)
        if sound_file:
            in_data_ = np.int16(audio_data_one*32767)
            sound_file.writeframes(in_data_.tostring())
        if len(voiced_buffer)>0 and num_unvoiced > 0.90 * NUM_WINDOW_CHUNKS:
            STATE['main'] = 2
            if sound_file:
                sound_file.close()
                sound_file=None
                AUDIOS.append((datetime.now(),filename_wav))
                ring_buffer_index=0
                voiced_buffer=np.array([],dtype='float16')
                ring_buffer_flags = [0] * NUM_WINDOW_CHUNKS
    return None

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
    SPEECHREC=False
    TTS=None

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


