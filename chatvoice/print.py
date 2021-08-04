# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import click
from click_option_group import optgroup
import sys
import configparser
import os.path

# local imports
from .conversation import Conversation
#from audio import audio_close, audio_devices, list_voices

# Main service
CONFIG='DEFAULT'
config = configparser.ConfigParser()
@click.group()
@click.option('--config-filename', type=click.Path(), default="config.ini")
@click.option("-v", "--verbose",
        is_flag=True,
        help="Verbose mode [%(default)s]")
@click.pass_context
def cli(ctx,conversation_file=None,config_filename="config.ini",verbose=False):
    global CONFIG
    global config
    ctx.ensure_object(dict)
    if os.path.exists(config_filename):
        config.read(config_filename)
    if conversation_file:
        extra_settings=os.path.splitext(os.path.basename(conversation_file))[0]
        if extra_settings in config:
            CONFIG=extra_settings
    ctx.obj['config']=config
    ctx.obj['conversation_file']=conversation_file
    ctx.obj['config_section']=CONFIG
    ctx.obj['verbose']=verbose

@cli.command()
@click.option("--conversation-file", type=click.Path(exists=True))
@click.option("--print-config", type=str,
        is_flag=True,
        help="Print values of config")
@click.option(
        "--devices",
        is_flag=True,
        help="List audio devices")
@click.option(
        "--local-tts-voices",
        is_flag=True,
        help="List voices from local TTS")
@click.option("--google-tts-languages",
        is_flag=True,
        help="List languages for google languages")
@click.pass_context
def info(ctx,conversation_file,devices,print_config,local_tts_voices,google_tts_languages):
    """Print information fo the system"""
    if devices:
        for info in audio_devices():
            print(info)
    if print_config:
        for sec in config:
            print(f'[{sec}]')
            for key,val in config[sec].items():
                print(f'{key}={val}')
            print()
    if local_tts_voices:
        list_voices(engine='local')
    if google_tts_languages:
        list_voices(engine='google')


if __name__ == '__main__':
    cli(obj={})
