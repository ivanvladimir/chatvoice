#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

import random

def execute(*args):
    var=args[0]
    opts=args[1]
    msg = random.choice(['hola','buen día','chevere','buenas tardes']+opts)
    return 'set_slot {0} "{1}"'.format(var,msg)

