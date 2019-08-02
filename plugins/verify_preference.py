#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# Janine 2019
# GPL 3.0

def verify(*preference):
    var = preference[0]
    preferencia = preference[1]
    #Quito los espacios
    preferencia = preferencia.replace(" ","")
    #valido si es una cadena numérica
    if preferencia.isdigit():
        msg = 1
    else:
        #la preferencia no es solo un numero
        msg = 0
    return 'set_slot {0} "{1}"'.format(var,str(msg))
