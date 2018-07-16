#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse
import sys
import os.path


# local imports
import conversation
from audio import audio_connect, audio_close, audio_devices, set_audio_dirname


if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
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
    p.add_argument("--channels",type=int,default=2,
            action="store", dest="channels",
            help="Number of channels microphone (1|2|...)")
    p.add_argument("--device",type=int,default=None,
            action="store", dest="device",
            help="Device number to connect audio")
    p.add_argument("--aggressiveness",type=int,default=None,
            action="store", dest="aggressiveness",
            help="VAD aggressiveness")
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
    #audio_connect(samplerate=args.samplerate,device=args.device,activate=args.rec_voice, channels=args.channels)
    conversation = conversation.Conversation(
            filename=args.CONV,
            verbose=args.verbose,
            tts=tts,
            rec_voice=args.rec_voice,
            channels=args.channels
            )
    conversation.execute()

    print("Summary values:")
    for val,k in conversation.slots.items():
        print(val,k)
