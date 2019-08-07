import json
import numpy as np
import random_questions

#conexion con la base de datos de platillos de desayuno, comida, cena y colacion
import sqlite3
connection_platillos = sqlite3.connect('conversations/platillos.db')
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


def conversacion_diaria(*intencion):
    respuesta_bella=intencion[0]
    var = intencion[1]
    #print( var)
    #print(respuesta_bella)
    import sqlite3
    connection_platillos = sqlite3.connect("../chatvoice/conversations/platillos.db")
    cursor_platillo = connection_platillos.cursor()
    #var = intencion
    #print(var)
    #print(type(var))
    #print(str(len(var)))

    #dar recomendacion de comida
    if var == "set_slot watson \"pedir_comida\"":
        horario = 'comida'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Te gustaría comer " + ms
        #return 'set_slot {0} "{1}" '.format("respuesta".msg)
        #print(msg)
    #dar recomendacion de desayuno
    elif var == "set_slot watson \"pedir_desayuno\"":
        horario = 'desayuno'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Se te antoja de desayuno probar " + ms
        #print( str(msg))
    #dar recomendacion de cena
    elif var == "set_slot watson \"pedir_cena\"":
        horario = 'cena'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Tal vez te gustaría cenar " + ms
        #print(str(msg))
    #dar recomendacion de colacion
    elif var == "set_slot watson \"peticion_colacion\"":
        horario = 'colacion'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Qué tal si de colación comes " + ms
        #print(str(msg))
    #dar respuesas acerca del peso
    elif var == "set_slot watson \"chequeo_peso\"":
        msg = "Disculpa. Sigo trabajando en el chequeo de peso"
        #print(str(msg))
    #dar respuesas acerca del monitoreo del progreso
    elif var == "set_slot watson \"monitoreo\"":
        msg = "Disculpa. Sigo trabajando en el monitoreo de peso"
        #print(str(msg))
    #dar respuesas acerca de Bella
    elif var == "set_slot watson \"dudas_de_bella\"":
        msg = "Mi nombre es Bella y mi objetivo es apoyarte dandote recomendaciones de platillos todas las veces por las que preguntes por algo de desayunar, comer o cenar, o incluso con alguna colación. Así te daré ideas de lo que puedes comer para que no te aburras con esta dieta de cero azucares y cero harinas  y logres alcanzar la meta de tu peso ideal"
        #print(str(msg))
    #dar respuesas acerca de la dieta
    elif var == "set_slot watson \"dudas_de_dieta\"":
        msg = "La dieta consta de evitar lo mas posible los alimentos que tengan harinas o azucares para poder bajar de peso. Con esto tú podrías disminuir de talla lo de 9 kilos si eres mujer o incluso, lo de 12 kilos en el caso de que seas hombre. Esta dieta dura 6 semanas y consta de 3 etapas. Así que aunque, yo solo sea la encargada de la primer etapa, TÚ podrás pedirme las recomendaciones de platillos para el desayuno, comida, cena o entre comidas, las veces que quieras por dos semanas. Las porciones son ilimitadas, así que puedes comer los platos que quieras"
        #print(str(msg))
    #dar diferente recomendacion de comida
    elif var == "set_slot watson \"pedir_sugerencia_diferente\"":
        horario = 'comida'
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE horario=? or picante=? or caldo=? or mar=? ORDER BY random() LIMIT 1;', (horario, picante, caldo, mar))
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Está bien. Entonces, que te parece " + ms
        #print(msg)
    #decirle al usuario qué puede preguntar
    elif var == "set_slot watson \"dudas_de_que_hacer\"":
        msg = excecute()
    #dar mensaje de despedida
    elif var == "set_slot watson \"despedida\"":
        msg = "Nos vemos luego."
        #print(str(msg))
    #dar mensaje de adios
    elif var == "set_slot watson \"no_quiere_algo_mas\"":
        msg = "De acuerdo, adiós."
    #Intentar pedir que diga algo de lo que podemos responder
    elif var == "set_slot watson \"dar_las_gracias_si_le_gusto\"":
        msg = "Me alegra ayudarte ¿Qué más puedo hacer por ti? "
    #dar recomendacion de comida picosa
    elif var == "set_slot watson \"pedir_algo_picante\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE picante=1 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si algo picante se te antoja, que te parece comer " + ms
    #dar recomendacion de comida no picosa
    elif var == "set_slot watson \"pedir_algo_no_picante\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE picante=0 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si lo que prefieres es algo que no pique, podrías comer " + ms
    #dar recomendacion de algo dulce
    elif var == "set_slot watson \"pedir_algo_dulce\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE dulce=1 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "No hay muchas opciones dulces pero, para librarte del antojo puedes comerte " + ms
    #dar recomendacion de comida de mar
    elif var == "set_slot watson \"pedir_algo_de_mar\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE mar=1 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si algo del mar es lo que se te antoja, podrías probar " + ms
    #dar recomendacion de comida caldosa
    elif var == "set_slot watson \"pedir_algo_caldoso\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE caldo=1 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si un caldito se te antoja, tal vez te gustaría comer " + ms
    else:
        msg = "Discúlpame, no entendí a qué te refieres."
        #print(str(msg))


    return 'set_slot {0} "{1}"'.format(respuesta_bella,str(msg))


f.close()

cursor_platillo.close()
connection_platillos.close()

#https://docs.python.org/3/library/sqlite3.html
#https://www.w3cschool.cn/doc_numpy_1_13/numpy_1_13-generated-numpy-random-choice.html
