#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# Janine 2019
# GPL 3.0

def verify_goal(*goal_weight):
    var = goal_weight[0]
    peso_objetivo = goal_weight[1]
    #Quito los espacios
    peso_objetivo = peso_objetivo.replace(" ","")
    #valido si es una cadena numérica
    if peso_objetivo.isdigit():
        peso_objetivo = float(peso_objetivo)
        if (40 < peso_objetivo) and (peso_objetivo < 597):
            #el peso objetivo está en un rango adecuado
            msg = 1
        else:
            #el peso objetivo no está en un rango adecuado
            msg = 0
    else:
        #el peso no es un número
        msg = 2
    return 'set_slot {0} "{1}"'.format(var,str(msg))
