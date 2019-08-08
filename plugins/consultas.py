import json
import numpy as np
import random

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
        msg = "Disculpa. Sigo trabajando en el chequeo de peso pero, te puedo comentar que en dos semanas podrías llegar a bajar de 3 a 6 kilos si logras eliminar de tu dieta diaria todas las harinas y todo el azúcar. Pero si tienes dudas de la dieta puedes preguntarme por ella así \'Bella, háblame de la dieta\'."
        #print(str(msg))
    #dar respuesas acerca del monitoreo del progreso
    elif var == "set_slot watson \"monitoreo\"":
        msg = "Disculpa. Sigo trabajando en el monitoreo de peso pero, te puedo comentar que en dos semanas podrías llegar a bajar de 3 a 6 kilos si logras eliminar de tu diaria todo lo que tenga harina o azucar. Si quieres saber más de la dieta pregúntame por ella diciendo algo así \'Platícame más de la dieta, Bella\'."
        #print(str(msg))
    #dar respuesas acerca de Bella
    elif var == "set_slot watson \"dudas_de_bella\"":
        msg = "Mi nombre es Bella, soy un bot diseñado para dar sugerencias de platillos para desayunar, comer o cenar, o incluso para alguna colación, siguiendo tus gustos de lo que prefieres respecto a la comida picante, de caldo o de mar, con el fin de que logres seguir al 100 tu dieta de cero azúcares y cero harinas. También puedo platicarte un poco de la misma dieta, así como de los alimentos que puedes comer o darte ejemplos de los que no. Aunque algunas veces me tardo un poco en responder, siempre lo hago. Si es que alguna vez te llego a confundir y no sabes qué puedes preguntarme, con confianza tú dime: \'¿Que te puedo preguntar?\' ó \'No sé qué hacer\' y yo siempre te sugeriré una pregunta diferente."
        #print(str(msg))
    #dar respuesas acerca de la dieta
    elif var == "set_slot watson \"dudas_de_dieta\"":
        msg = "Esta dieta, específica para bajar de peso, consta de evitar a toda costa los alimentos que tengan harinas o azúcares por dos semanas, así que todos los demás alimentos como carnes, quesos o verduras, son los que deberás comer en las porciones que logren satisfacer tu hambre, así que estás pueden ser ilimitadas; por lo que nunca tendrás que preocuparte por el conteo de calorias. Para los tiempos, yo te recomiendo no pasar más de 4 horas de ayuno, así que entre comida puedes incluir alguna colación ¡y para eso yo te puedo ayudar recomendandote alguna también!. Si quieres algunos ejemplos de lo que NO puedes comer, tú puedes preguntarme por ellos."
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
        msg = (random.choice(['Puedes decir \'¿Qué me sugieres comer hoy?\' y yo te doy una recomendación de platillo. ','Puedes decirme \'Sugiéreme algo para desayunar\' y yo te sugiero un platillo para tu desayuno.','Podrías decirme \'¿Qué podría cenar hoy?\' y yo te doy una sugerencia.','Puedes decirme \'Recomiendame algo dulce\' y yo te daré una sugerencia..','Puedes decirme \'Se me antoja algo picoso\' y yo te lo recomiendo.','Puedes decirme \'Quisiera comer algo sin chile\' y claro que yo te recomiendo algo.', 'Puedes decirme \'Bella, háblame de tí\' y yo te platico un poquito de mí.', 'Puedes decirme \'Quiero saber de la dieta\' y yo te platico un poquito de la dieta.']))
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
    #dar recomendacion de comida no de mar
    elif var == "set_slot watson \"pedir_algo_no_de_mar\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE mar=0 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si prefieres algo que no sea comida de mar, podrías probar " + ms
    #dar recomendacion de comida caldosa
    elif var == "set_slot watson \"pedir_algo_caldoso\"":
        consulta = cursor_platillo.execute('SELECT platillo FROM platillos WHERE caldo=1 ORDER BY random() LIMIT 1;')
        m = cursor_platillo.fetchone()
        ms = m[0]
        msg = "Si un caldito se te antoja, tal vez te gustaría comer " + ms
    #dar respuesta a consulta de un alimento en especifico
    elif var == "set_slot watson \"consultar_alimento\"":
        msg = "Aún no logro ser tan específica para explicar cada platillo pero, estoy trabajando en ello. Aunque lo que sí te puedo decir es que puedes comer lo que sea, carne, verduras, quesos, con la única restricción de que no tenga harina o azúcar. Así que nada de tortillas, papas o fruta pero si quieres algunos ejemplos más detallados de lo que no deberías comer puedes preguntarme por ellos así \'¿Que cosas no puedo comer?\'."
    #dar respuesta a consulta de alimentos no permitidos
    elif var == "set_slot watson \"peticion_de_que_no_comer\"":
        msg = "En general, todo aquello con azúcar o harina está prohibido. Pero para ser más específica, por mencionar algunos ejemplos de lo que no debes comer te enlisto las tortillas, el bolillo, las galletas saladas, la sopida de fideo u otras pastas, la leche, los jugos, el refresco, cualquier fruta, los frijoles, el arroz, el garbanzo, la papa, la zanahoria; o cualquier guisado o platillo que los contenga. Aunque si tienes antojo de algo dulce tú puedes preguntarme \'¿que cosas dulces puedo comer?\' y yo con gusto te ayudo."
    #dar respuesta de lo que contiene un platillo
    elif var == "set_slot watson \"aclaracion_de_lo_que_es\"":
        msg = "Disculpa, aun no logro aprenderme las recetas y lo que lleva cada platillo pero te puedo decir que no lleva ni harina o azucar, aunque si quieres saber que cosas son las que NO puedes comer puedes decirme \'Bella ¿que es lo que no puedo comer?\' y yo te daré algunos ejemplos."
    else:
        msg = "Discúlpame, no entendí a qué te refieres. Aunque si me pidieras una recomendación de lo que puedes comer hoy, seguro que eso sí te lo respondería."
        #print(str(msg))


    return 'set_slot {0} "{1}"'.format(respuesta_bella,str(msg))


f.close()

cursor_platillo.close()
connection_platillos.close()

#https://docs.python.org/3/library/sqlite3.html
#https://www.w3cschool.cn/doc_numpy_1_13/numpy_1_13-generated-numpy-random-choice.html
