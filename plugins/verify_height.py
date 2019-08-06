#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# Janine 2019
# GPL 3.0

def verify(*height):
    var = height[0]
    estatura = height[1]
    #Quito los espacios
    estatura = estatura.replace(" ","")
    #valido si es una cadena numérica
    if estatura.isdigit():
        estatura = float(estatura)
        if (140 < estatura) and (estatura < 200):
            #la estatura está en un rango adecuado
            msg = 1
        else:
            #la estatura no está en un rango adecuado
            msg = 0
    else:
        #la estatura no es un número
        msg = 2
    return 'set_slot {0} "{1}"'.format(var,msg)
