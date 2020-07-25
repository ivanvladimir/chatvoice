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
import server

# local imports
import conversation

# load config
config = configparser.ConfigParser()
if os.path.exists("config.ini"):
    config.read('config.ini')

if __name__ == '__main__':
    p = argparse.ArgumentParser("preprocessing",add_help=False)
    p.add_argument("--config_section",default="DEFAULT",
            help="Section of the config file")
    kargs,extra = p.parse_known_args()

    if kargs.config_section in config:
        CONFIG=kargs.config_section

    p = argparse.ArgumentParser("chatserver")
    p.add_argument("-W","--webinterface",
            action="store_true",
            help="Run webinterface [%(default)s]")
    g13 = p.add_argument_group('Webinterface', 'Webinterface settings')
    g13.add_argument("--host",
            default=config.get(CONFIG,'host',fallback='127.0.0.1'),
            action="store",
            help="Host [%(default)s]")
    g13.add_argument("--port",
            default=config.getint(CONFIG,'port',fallback=5000),
            type=int, action="store",
            help="Port [%(default)s]")
    p.add_argument("-v", "--verbose",
            action="store_true",
            help="Verbose mode [%(default)s]")

    args = p.parse_args(extra)

    CONFIG={}
    for k, v in config[kargs.config_section].items():
        if v == 'False':
            CONFIG[k]=False
        elif v == 'True':
            CONFIG[k]=True
        else:
            try:
                CONFIG[k]=int(v)
            except ValueError:
                CONFIG[k]=v
    CONFIG.update(vars(args))
    
    web,app=server.start_server(CONFIG)
    web.run_app(app,
        host=CONFIG['host'],
        port=CONFIG['port'])
