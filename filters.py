#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0
import dateparser

def yesno(msg,*args):
    if msg in ['si','sí']:
        return True
    else:
        return False

def fecha(msg,*args):
    return dateparser.parse(u''+msg)

def number(msg,*args):
    msg=msg.lower()
    dicc = {'ninguno':0,'cero':0,'uno':1,'dos':2,'tres':3,'cuatro':4,'cinco':5,'seis':6,'siete':7,'ocho':8,'nueve':9,'diez':10}
    if msg in ['ninguno','cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve','diez']:
        return dicc[msg]
    else:
        return float(msg)

def list(msg,*args):
    return msg.split()

def asign(msg,*args):
    for k_a in args:
        k,a = k_a.split(':',1)
        if msg.find(k)>=0:
            return a
    return 'None'
