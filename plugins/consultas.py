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
if int(y["preference_spicy"]) <= 2:
    picante = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif int(y["preference_spicy"]) == 3:
    picante = np.random.randint(0,1,1)
else:
    #generar una muestra del tamaño de un elemento a partir
    #de dos elementos que son el 0 y el 1 con probabilidad
    #de elegir 0 (negativo a...) con p=0.2 y
    #de elegir 1 (positivo a...) con p=0.8.
    #que es la medicion de la preferencia
    picante = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de caldos de acuerdo el gusto del usuario
if int(y["preference_soup"]) <= 2:
    caldo = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif int(y["preference_soup"]) == 3:
    caldo = np.random.randint(0,1,1)
else:
    caldo = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de comida de mar de acuerdo el gusto del usuario
if int(y["preference_seafood"]) <= 2:
    mar = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif int(y["preference_seafood"]) == 3:
    mar = np.random.randint(0,1,1)
else:
    mar = np.random.choice(2, 1, replace=True, p=[0.2,0.8])

#definir preferencia de sabor dulce de acuerdo el gusto del usuario
if int(y["preference_sweet"]) <= 2:
    dulce = np.random.choice(2, 1, replace=True, p=[0.8,0.2])
elif int(y["preference_sweet"]) == 3:
    dulce = np.random.randint(0,1,1)
else:
    dulce = np.random.choice(2, 1, replace=True, p=[0.2,0.8])


var = ''

def conversacion_diaria(intencion):
    import sqlite3
    connection_platillos = sqlite3.connect("/home/ljanine/repo/chatvoice/conversations/platillos.db")
    cursor_platillo = connection_platillos.cursor()
    var = intencion
    #print(var)
    #print(type(var))
    #print(str(len(var)))

    #dar recomendacion de comida
    if var == "set_slot watson \"pedir_comida\"":
        horario = 'comida'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Que te parecería comer " + ms
        print(msg)
    #dar recomendacion de desayuno
    elif var == "set_slot watson \"pedir_desayuno\"":
        horario = 'desayuno'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        msg = cursor_platillo.fetchone()
        msg = msg[0]
        msg = "Que te parecería comer " + msg
        print( str(msg))
    #dar recomendacion de cena
    elif var == "set_slot watson \"pedir_cena\"":
        horario = 'cena'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        msg = cursor_platillo.fetchone()
        msg = msg[0]
        msg = "Que te parecería comer " + msg
        print(str(msg))
    #dar recomendacion de colacion
    elif var == "set_slot watson \"peticion_colacion\"":
        horario = 'colacion'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        msg = cursor_platillo.fetchone()
        msg = msg[0]
        msg = "Que te parecería comer " + msg
        print(str(msg))
    #dar respuesas acerca del peso
    elif var == "set_slot watson \"chequeo_peso\"":
        msg = "Disculpa. Sigo trabajando en el chequeo de peso"
        print(str(msg))
    #dar respuesas acerca del monitoreo del progreso
    elif var == "set_slot watson \"monitoreo\"":
        msg = "Disculpa. Sigo trabajando en el monitoreo de peso"
        print(str(msg))
    #dar respuesas acerca de Bella
    elif var == "set_slot watson \"dudas_de_bella\"":
        msg = "Disculpa. Sigo trabajando en poder solucionar tus dudas"
        print(str(msg))
    #dar respuesas acerca de la dieta
    elif var == "set_slot watson \"dudas_de_dieta\"":
        msg = "Disculpa. Sigo trabajando en poder solucionar tus dudas"
        print(str(msg))
    #dar diferente recomendacion de comida
    elif var == "set_slot watson \"pedir_sugerencia_diferente\"":
        horario = 'comida'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Está bien. Entonces, que te parece " + ms
        print(msg)
    #dar mesnaje de despedida
    elif var == "set_slot watson \"despedida\"":
        msg = "Adiós"
        print(str(msg))
    #Intentar pedir que diga algo de lo que podemos responder
    else:
        msg = "Disculpa, no te entendí."
        print(str(msg))

    
    

    return 'set_slot {0} "{1}"'.format("respuesta",str(msg))

f.close()

cursor_platillo.close()
connection_platillos.close()

#https://docs.python.org/3/library/sqlite3.html
#https://www.w3cschool.cn/doc_numpy_1_13/numpy_1_13-generated-numpy-random-choice.html
