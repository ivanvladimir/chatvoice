#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse
import sys


# local imports
import conversation
from audio import audio_connect, audio_close, audio_devices


if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
    p.add_argument("CONV",
            help="Conversation file")
    p.add_argument("--list_devices",
            action="store_true", dest="list_devices",
            help="List audio devices")
    p.add_argument("--google_tts",
            action="store_true", dest="google_tts",
            help="Use google tts")
    p.add_argument("--samplerate",type=int,default=16000,
            action="store", dest="samplerate",
            help="Samplerate")
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
    else:
        tts="local"

    if args.aggressiveness:
        vad_aggressiveness(args.aggressiveness)
    audio_connect(samplerate=args.samplerate,device=args.device)
    conversation = conversation.Conversation(
            filename=args.CONV,
            verbose=args.verbose,
            tts=tts,
            )
    conversation.execute()

    print("Summary values:")
    for val,k in conversation.slots.items():
        print(val,k)
