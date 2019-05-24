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


#print(y['name'])

def verify(*nombre):
    var=nombre[0]
    name_user=nombre[1]


    #comparar que SÍ existe en la base de datos
    if name_user == y["name"]:
        msg=1

    #comprobado que NO existe
    else :
        msg=0


    return 'set_slot {0} "{1}"'.format(var,str(msg))

f.close()
