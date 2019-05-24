#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# CARMEN Y YUMIN 2019
# GPL 3.0

import json


with open('/home/ljanine/repo/chatvoice/conversations/kb.db','r') as f:
    data = f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)

name_user=input("dame tu nombre")
#comparar que SÍ existe en la base de datos
if name_user == 'janine':
   msg=1
   print(msg)
#comprobado que NO existe
else :
    msg=0
    print(msg)


f.close()

