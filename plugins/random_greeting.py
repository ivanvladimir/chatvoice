#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

import random

def execute(*args):
    var=args[0]
    opts=args[1]
    msg = random.choice(['Hola','Buenas tardes','Buen dia']+opts)
    #msg_noche = random.choice(['Hola','Buenas noches']+opts)     lista de saludo para horario de noche
    #msg_noche = random.choice(['Hola','Buenos dias']+opts)     lista de saludo para horario de la ma;ana
    #descubrir como pedir la hora del sistema para definir de que lista tomara el saludo
    return 'set_slot {0} "{1}"'.format(var,msg)

