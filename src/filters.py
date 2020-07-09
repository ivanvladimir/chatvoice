#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

def yesno(msg,*args):
    if msg in ['si','sí']:
        return True
    else:
        return False

def number(msg,*args):
    return float(msg)

def list(msg,*args):
    return msg.split()

def asign(msg,*args):
    for k_a in args:
        k,a = k_a.split(':',1)
        if msg.find(k)>=0:
            return a
    return 'None'
