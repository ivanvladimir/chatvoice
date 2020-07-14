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
from pathlib import Path

if __name__ == '__main__':
    p = argparse.ArgumentParser("create_new")
    p.add_argument("CONVDIR",nargs='?',
            help="Conversation file")
    p.add_argument("-n", "--name", default='CHATVOICE',
            action="store",
            help="Name for chatbot  [%(default)s]")
    p.add_argument("-p", "--path", default='conversations',
            action="store",
            help="Path for conversation  [%(default)s]")
    p.add_argument("-m", "--main", default='main.yaml',
            action="store",
            help="Namefile for main  [%(default)s]")
    p.add_argument("-v", "--verbose",
            action="store_true",
            help="Verbose mode [%(default)s]")

    args = p.parse_args()

    main=f"""
settings:
    name: {args.name}

strategies:
    name:
        - say "mi nombre is {args.name}"

script:
    - solve name
"""

    os.mkdir(os.path.join(args.path,args.CONVDIR))
    with open(os.path.join(args.path,args.CONVDIR,args.main),"w",encoding="utf-8") as f:
        f.write(main)
    os.mkdir(os.path.join(args.path,args.CONVDIR,'plugins'))
    Path(os.path.join(args.path,args.CONVDIR,'plugins','__init__.py')).touch()
