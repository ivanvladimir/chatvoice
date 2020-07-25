#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0
import re

re_number=re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?')

def yesno(msg,*args):
    if msg in ['si','sí']:
        return True
    else:
        return False

def number(msg,*args):
    m=re_number.search(msg)
    if m:
        print('N',m.group(0))
        return float(m.group(0))
    else: 
        return 'UNK'

def reexp(msg,*args):
    print(msg,*args)

def list(msg,*args):
    return msg.split()

def asign(msg,*args):
    for k_a in args:
        k,a = k_a.split(':',1)
        if msg.find(k)>=0:
            return a
    return 'None'
