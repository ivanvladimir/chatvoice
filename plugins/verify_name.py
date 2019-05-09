#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# CARMEN Y YUMIN 2019
# GPL 3.0

import json


with open('/home/ljanine/repo/chatvoice/conversations/name.db','r') as f:
    data = f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)


def verify_name(*arg):
    var=args[0]
    name_user=args[1]

    #comparar que SÍ existe en la base de datos
    if y['name'] == name_user:
        msg=1
    #comprobado que NO existe
    elif :
        msg=0


return 'set_slot {0} "{1}"'.format(var,str(msg))

f.close()
