import numpy as np
import sqlite3
connection_platillos = sqlite3.connect("/home/pi/Documents/cb_nutricion/chatvoice/conversations/kb.db")
cursor_platillo = connection_platillos.cursor()

horario = 'comida'
picante  =  np.random.choice(2, 1, replace=True, p=[0.2,0.8])
caldo = np.random.choice(2, 1, replace=True, p=[0.2,0.8])
mar = np.random.choice(2, 1, replace=True, p=[0.2,0.8])
dulce = np.random.randint(0,1,1)

picante =1
caldo = 0
mar = 1
dulce = 0

consulta = cursor_platillo.execute('SELECT * FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ', (horario, picante, caldo, mar))
msg = cursor_platillo.fetchone()

consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ', (horario, picante, caldo, mar))
msg2 = cursor_platillo.fetchone()

print(type(msg))
print(msg)
print(msg[1])
print(picante)
print(caldo)
print(mar)
print(dulce)
#los buenos
print(msg2)
#el mero mero bueno
print(msg2[0])
