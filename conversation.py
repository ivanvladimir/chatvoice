#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

import yaml


class Conversation:
    def __init__(self, filename=None, definition=None):
        if filename:
            with open(filename, 'r') as stream:
                try:
                    definition=yaml.load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
        if definition:
            self.load_conversation(definition)

    def load_conversation(definition):
        print(definition)

