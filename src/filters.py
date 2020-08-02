#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0
import re
import os.path

re_number=re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?')

def yesno(self,msg,*args):
    if msg in ['si','sí']:
        return True
    else:
        return False

def number(self,msg,*args):
    m=re_number.search(msg)
    if m:
        print('N',m.group(0))
        return float(m.group(0))
    else: 
        return 'UNK'

def regex(self,msg,*args):
    if len(args)==0:
        return msg
    if len(args)>0:
        exps=self.regex[args[0]]
    for exp in exps:
        m=re.search(exp,msg)
        if m:
            if len(args)==1:
                return m.group(0)
            if len(args)==2:
                selector=args[1]
                if selector=='ALL':
                    return m.groupdict()
                try:
                    num=int(args[1])
                    return m.group(num)
                except ValueError:
                    return m.group(args[1])
    return 'UNK'

def list(self,msg,*args):
    return msg.split()

def asign(self,msg,*args):
    for k_a in args:
        k,a = k_a.split(':',1)
        if msg.find(k)>=0:
            return a
    return 'None'

nlps={}
def model(self,msg,*args):
    if len(args)==0:
        return msg
    if len(args)==1:
        if not args[0] in nlps.keys():
            from transformers import pipeline
            nlps[args[0]] = pipeline('ner',os.path.join('models',args[0]))
        res=[ (lab['word'],lab['entity']) for lab in nlps[args[0]](msg.lower()) if not lab['word'] == "[CLS]"]
        res_=[]
        for w,l in res:
            if l.startswith('I'):
                res_[-1]=f"{res_[-1]} {w}"
            else:
                res_.append(w)
    return res_
