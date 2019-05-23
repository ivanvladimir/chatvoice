import json
import numpy as np
import sqlite3
import time
import datetime
from datetime import datetime, timedelta



with open('/home/krmn/Documentos/IIMAS/chatvoice/conversations/kb.db','r') as f:
    data =f.readlines()
for x in data:
    json.dumps(x)
y = json.loads(x)

weight_ini=float(y["weight_ini"])
ahora=datetime.now().date()
nombre=y["name"]

connection_seguimiento = sqlite3.connect("/home/krmn/Documentos/IIMAS/chatvoice/conversations/seguimiento.db")
cursor_seguimiento = connection_seguimiento.cursor()


#cursor_seguimiento . execute ( "INSERT INTO objetivo (nombre, fecha, peso) VALUES (?,?,?)", (nombre, ahora, weight_ini))
cursor_seguimiento . execute ( "INSERT INTO objetivo (nombre, fecha, peso) SELECT ?, ?, ? FROM objetivo WHERE NOT EXISTS(SELECT * FROM objetivo where nombre=? and fecha=?)", (nombre, ahora, weight_ini, nombre, ahora))
#print ("consulta")
consulta = cursor_seguimiento . execute ( "select fecha from objetivo where post_id=2 and nombre=?", (nombre,))
m = cursor_seguimiento.fetchone()
ms = m[0]
#print (ms)

formato = "%Y-%m-%d"
ms = datetime.strptime(ms, formato).date()
print (ms)

contador = ms + timedelta(days=0)
print (contador)

if contador == ahora:
	print ("Hola {} , recuerdas que dariamos seguimiento a tu peso,  ¡pues hoy es el dia de checarnos!" .format(nombre))
	weight_goal = input('¿Puedes decirme cuanto pesas el día de hoy?\n')
	cursor_seguimiento . execute ( "INSERT INTO objetivo (nombre, fecha, peso) VALUES (?,?,?)", (nombre, ahora, weight_goal))

	

	
connection_seguimiento.commit()
cursor_seguimiento . close ()
