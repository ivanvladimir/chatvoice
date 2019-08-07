#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# Janine
# GPL 3.0

import random

def execute(*args):
    var=args[0]
    opts=args[1]
    msg = (random.choice(['Puedes decir \"¿qué me sugieres comer hoy?\" y yo te doy una recomendación de platillo. ','Puedes decirme \"Sugiéreme algo para deCsayunar\" y yo te sugiero un platillo para tu desayuno.','Podrías decirme \"¿que podría cenar hoy?\"','Puedes decirme \"Recomiendame algo dulce\".','Puedes decirme \"Se me antoja algo picoso\" y yo te lo recomiendo.','Puedes decirme \"Quisiera comer algo sin chile\"y claro que yo te recomiendo algo.', 'Puedes decirme \"Bella, háblame de tí\" y yo te platico un poquito de mí.', 'Puedes decirme \"Quiero saber de la dieta\" y yo te platico un poquito de la dieta.']+opts))
    return 'set_slot {0} "{1}"'.format(var,msg)
