import json
import numpy as np
import sqlite3
import time
import datetime
from datetime import datetime, timedelta



with open('/home/ljanine/repo/chatvoice/conversations/kb.db','r') as f:
    data =f.readlines()
for x in data:
    json.dumps(x)
y = json.loads(x)

weight_ini=float(y["weight_ini"])
ahora=datetime.now().date()
nombre=y["name"]

connection_seguimiento = sqlite3.connect("/home/ljanine/repo/chatvoice/conversations/seguimiento.db")
cursor_seguimiento = connection_seguimiento.cursor()
peso1=0
peso2=0
peso3=0
print(nombre)
#cursor_seguimiento . execute ( "INSERT INTO objetivo (nombre, fecha, peso) VALUES (?,?,?)", (nombre, ahora, weight_ini))
cursor_seguimiento . execute ( "INSERT INTO objetivo (nombre, fecha, peso, peso1, peso2, peso3) VALUES(?,?,?,?,?,?) WHERE NOT EXISTS(SELECT * FROM objetivo where nombre=? and fecha=?)", (nombre, ahora, weight_ini, peso1, peso2, peso3,nombre,ahora))
consulta = cursor_seguimiento . execute ( "Select fecha from objetivo where nombre=?",(nombre,))
m = consulta.fetchone()
ms = m[ 0 ]

formato = "%Y-%m-%d"
ms = datetime.strptime(ms, formato).date()

contador = ms + timedelta(days=0)
print (contador)
if contador == ahora:
	print ("Hola {} , recuerdas que dariamos seguimiento a tu peso,  ¡pues hoy es el dia de checarnos!" .format(nombre))
	weight_actual = input('¿Puedes decirme cuanto pesas el día de hoy?\n')
	cursor_seguimiento . execute ( "UPDATE objetivo SET peso1 = ? where nombre=?",  (weight_actual, nombre, ))



contador2 = ms + timedelta(days=1)
print (contador2)
if contador2 == ahora:
    print ("Hola {} , recuerdas que dariamos seguimiento a tu peso,  ¡pues hoy es el dia de checarnos!" .format(nombre))
    weight_actual1 = input('¿Puedes decirme cuanto pesas el día de hoy?\n')
    cursor_seguimiento . execute ( "UPDATE objetivo SET peso2 = ? where nombre=?", (weight_actual1, nombre, ))

contador3 = ms + timedelta(days=2)
print (contador3)
if contador3 == ahora:
    print ("Hola {} , recuerdas que dariamos seguimiento a tu peso,  ¡pues hoy es el dia de checarnos!" .format(nombre))
    weight_actual2 = input('¿Puedes decirme cuanto pesas el día de hoy?\n')
    cursor_seguimiento . execute ( "UPDATE objetivo SET peso3 = ? where nombre=?",  (weight_actual2, nombre, ))
	
connection_seguimiento.commit()
cursor_seguimiento . close ()
