#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

def yesno(msg):
    if msg in ['si','sí']:
        return True
    else:
        return False

def number(msg):
    return float(msg)

def list(msg):
    return msg.split()
