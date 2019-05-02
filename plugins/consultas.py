import json

import numpy as np

#conexion con la base de datos de platillos de desayuno, comida, cena y colacion
import sqlite3
connection_platillos = sqlite3.connect("/home/ljanine/repo/chatvoice/conversations/platillos.db")
cursor_platillo = connection_platillos.cursor()

#conexion con la base de datos del usuario
with open('/home/ljanine/repo/chatvoice/conversations/kb.db','r') as f:
    data =f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)

#variables de preferencias que se adecuaran a cada usuario
picante = 0
caldo = 0
mar = 0
dulce = 0

#definir preferencia de picante de acuerdo el gusto del usuario
if y["preference_spicy"] <= 2:
	picante = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif y["preference_spicy"] == 3:
	picante = np.random.randint(0,1,1)
else:
	#generar una muestra del tamaño de un elemento a partir
	#de dos elementos que son el 0 y el 1 con probabilidad
	#de elegir 0 (negativo a...) con p=0.2 y
	#de elegir 1 (positivo a...) con p=0.8.
	#que es la medicion de la preferencia
	picante = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de caldos de acuerdo el gusto del usuario
if y["preference_soup"] <= 2:
	caldo = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif y["preference_soup"] == 3:
	caldo = np.random.randint(0,1,1)
else:
	caldo = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de comida de mar de acuerdo el gusto del usuario
if y["preference_seafood"] <= 2:
	mar = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif y["preference_seafood"] == 3:
	mar = np.random.randint(0,1,1)
else:
	mar = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de sabor dulce de acuerdo el gusto del usuario
if y["preference_sweet"] <= 2:
	dulce = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif y["preference_sweet"] == 3:
	dulce = np.random.randint(0,1,1)
else:
	dulce = np.random.choice(2, 1, replace=True, p=[0.2,0.8])



def conversacion_diaria(*args)
	var=args[0]

	#dar recomendacion de comida
	if prueba2.procesa_watson(var) == "pedir_comida":
		horario = 'comida'
		cursor_platillo.execute('SELECT * FROM platillos WHERE horario=? and picante=? and caldo=? and mar=? ', (horario, picante, caldo, mar))
		msg = "Que te parecería comer " + cursor_platillo.fetchone()

	#dar recomendacion de desayuno
	elif prueba2.procesa_watson(var) == "pedir_desayuno":
		horario = 'desayuno'
		cursor_platillo.execute('SELECT * FROM platillos WHERE horario=? and picante=? and caldo=? and mar=? ', (horario, picante, caldo, mar))
		msg = "Que te parecería comer " + cursor_platillo.fetchone()

	#dar recomendacion de cena
	else prueba2.procesa_watson(var) == "pedir_cena":
		horario = 'cena'
		cursor_platillo.execute('SELECT * FROM platillos WHERE horario=? and picante=? and caldo=? and mar=? ', (horario, picante, caldo, mar))
		msg = "Que te parecería comer " + cursor_platillo.fetchone()

	#dar recomendacion de colacion
	else prueba2.procesa_watson(var) == "peticion_colacion":
	    horario = 'colacion'
		cursor_platillo.execute('SELECT * FROM platillos WHERE horario=? and picante=? and caldo=? and mar=? ', (horario, picante, caldo, mar))
		msg = "Que te parecería comer " + cursor_platillo.fetchone()

	#dar respuesas acerca del peso
	else prueba2.procesa_watson(var) == "chequeo_peso":
		msg = "Disculpa. Sigo trabajando en el chequeo de peso"

	#dar respuesas acerca del monitoreo del progreso
	else prueba2.procesa_watson(var) == "monitoreo":
		msg = "Disculpa. Sigo trabajando en el monitoreo de peso"

	#dar respuesas acerca de Bella
	else prueba2.procesa_watson(var) == "#dudas_de_bella":
		msg = "Disculpa. Sigo trabajando en poder solucionar tus dudas"

	#dar respuesas acerca de la dieta
	else prueba2.procesa_watson(var) == "#dudas_de_dieta":
		msg = "Disculpa. Sigo trabajando en poder solucionar tus dudas"

	#Intentar pedir que diga algo de lo que podemos responder
	else:
		msg = "Disculpa, no te entendí."

return 'set_slot {0} "{1}"'.format(var,msg)

f.close()

cursor_platillo.close()
connection_platillos.close()

#https://docs.python.org/3/library/sqlite3.html
#https://www.w3cschool.cn/doc_numpy_1_13/numpy_1_13-generated-numpy-random-choice.html
