#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse
import sys
import configparser
import os.path
import yaml

# local imports
import conversation
from audio import audio_connect, audio_close, audio_devices, set_audio_dirname



# load config
config = configparser.ConfigParser()
if os.path.exists("config.ini"):
    config.read('config.ini')

if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
    p.add_argument("CONV",nargs='?',
            help="Conversation file")
    g1 = p.add_argument_group('Information', 'Display alternative information')
    g1.add_argument("--print_config",
            action="store_true",
            help="Print values of config")
    g1.add_argument("--list_devices",
            action="store_true",
            help="List audio devices")
    g11 = p.add_argument_group('Paths', 'Information to control paths')
    g11.add_argument("--audios_dir",default=config.get('DEFAULT','audios_dir',fallback='audios'),
            action="store",
            help="Directory for audios for speech recognition")
    g2 = p.add_argument_group('Speech', 'Options to control speech processing')
    g2.add_argument("--speech_recognition",
            action="store_true",
            help="Activate speech recognition")
    g2.add_argument("--google_tts",
            action="store_true", dest="google_tts",
            help="Use google tts")
    g2.add_argument("--local_tts",
            action="store_true", dest="local_tts",
            help="Use espeak local tts")
    g3 = p.add_argument_group('Audio', 'Options to control audio')
    g3.add_argument("--samplerate",type=int,
            default=config.getint('DEFAULT','samplerate',fallback=16000),
            action="store", dest="samplerate",
            help=f"Samplerate [%(default)s]")
    g3.add_argument("--channels",type=int,
            default=config.getint('DEFAULT','channels',fallback=2),
            action="store",
            help=f"Number of channels microphone [%(default)s]")
    g3.add_argument("--device",
            default=config.getint('DEFAULT','device',fallback=None),
            action="store",
            help="Device number to connect audio [%(default)s]")
    g3.add_argument("--aggressiveness",
            default=config.getint('DEFAULE','aggressiveness',fallback=None),
            action="store",
            help="VAD aggressiveness [%(default)s]")
    p.add_argument("-v", "--verbose",
            action="store_true",
            help="Verbose mode [%(default)s]")

    args = p.parse_args()

    # Modes that print alternative information
    if args.list_devices:
        for info in audio_devices():
            print(info)
        sys.exit()
    elif args.print_config:
        for sec in config:
            print(f'[{sec}]')
            for key,val in config[sec].items():
                print(f'{key}={val}')
            print()
        sys.exit()

    # setting defaults
    CONFIG={}
    for k,v in config['DEFAULT'].items():
        if k in ['speech_recognition']:
            CONFIG[k]=config.getboolean('DEFAULT','speech_recognition')
        else:
            CONFIG[k]=v
    if args.CONV:
        extra_settings=os.path.splitext(os.path.basename(args.CONV))[0]
        if extra_settings in config:
            CONFIG.update(config[extra_settings])
    else:
        print("No conversation file provided")
        sys.exit()

    # setting audio
    if args.samplerate:
        CONFIG['samplerate']=args.samplerate
    if args.channels:
        CONFIG['channels']=args.channels
    if args.device:
        CONFIG['device']=args.device
    if args.aggressiveness:
        CONFIG['aggressiveness']=args.aggressiveness

    # Setting paths
    if not 'main_path' in config['DEFAULT']:
        CONFIG['main_path']=os.getcwd()
    if args.audios_dir:
        CONFIG['audios_dir']=args.audios_dir

    # Setting TTS
    if args.google_tts:
        CONFIG['tts']="google"
    elif args.local_tts:
        CONFIG['tts']="local"
    else:
        CONFIG['tts']=None

    # speech
    audios_dir=os.path.join(CONFIG['main_path'],CONFIG['audios_dir'])
    if not os.path.exists(audios_dir):
        os.mkdir(audios_dir)
    set_audio_dirname(audios_dir)

    if args.aggressiveness:
        CONFIG['aggressiveness']=args.aggressiveness
        aggressiveness=args.aggressiveness
        vad_aggressiveness(aggressiveness)

    # Main loop
    conversation = conversation.Conversation(
            filename=args.CONV,
            verbose=args.verbose,
            **CONFIG)
    conversation.execute()

    print("Summary values:")
    for val,k in conversation.slots.items():
        print(val,k)
