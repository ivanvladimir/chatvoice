#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

import random

def execute(*args):
    msg = random.choice(['hola','buen día','chevere'])
    return 'say "{}"'.format(msg)

