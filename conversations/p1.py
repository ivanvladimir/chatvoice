import json 
from genderize import Genderize


with open('../conversations/kb.db','r') as f:
    data =f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)

#CALCULA CATEGORIA SEGUN IMC


def IMC(classification):
    if (classification<18.5):
        low_weight="Peso bajo"
        classification=low_weight
    elif (classification<24.9):
        normal_weight="Normal"
        classification=normal_weight
    elif (classification<29.9):
        overweight="Sobrepeso "
        classification=overweight
    elif (classification<34.9):
        obesityI="Obesidad I"
        classification=obesityI
    elif (classification<39.9):
        obesityII="Obesidad II"
        classification=obesityII
    else:
        obesityIII="Obesidad III"
        classification=obesityIII
    return classification




#DEFINE EL GÉNERO
   
results = Genderize().get([y["name"]])  # Genderize name(s) (String or List)
for res in results:                     # View results
    gender=res['gender']



#CALCULA IMC CON PESO ACTUAL Y PESO OBJETIVO

weight_ini=float(y["weight_ini"])
weight_goal=float(y["weight_goal"])
height=float(y["height"])/100

IMC_goal= weight_goal/(height**2)
IMC_ini= weight_ini/(height**2)


print ('{:.2f}'.format(IMC_ini))
print ('{:.2f}'.format(IMC_goal))
print (gender)


a=IMC(IMC_goal)
b=IMC(IMC_ini)

print(a,b)

if (weight_ini>weight_goal):
    if ((weight_ini-weight_goal)<=9): 
        if (IMC(IMC_goal)=="Normal"):
            if(IMC(IMC_goal)==IMC(IMC_ini)):
                print ("El peso objetivo esta dentro del rango Normal")
            if(IMC(IMC_goal)!=IMC(IMC_ini)):
                print ("Vale, vale. Si se puede cumplir el objetivo")
        if (IMC(IMC_goal)=="Peso bajo"):
            if(IMC(IMC_goal)==IMC(IMC_ini)):
                print ("Tu peso es ya muy bajo, deberias acudir con un nutriologo")
            if(IMC(IMC_goal)!=IMC(IMC_ini)):
                print ("El objetivo que nos propusimos no es sano.")                
    else:
        print("Ingrese nuevamente")


                                             


#"weight_goal": "60", "weight_ini": "68"

"""
if (gender == 'female'):
    
pesoI=float(y["weight_ini"])
pesoF=float(y["weight_goal"])

if (pesoI<pesoF):
    w=pesoI-pesoF
    if (w<9):
        print ("Esta dieta funcionará")
else:
    print ("Te aseguramos que bajaras 9 kilos")
"""
        

f.close()
#print (results)
#print (y["name"])
#print (gender)





    


#Validar el peso objetivo con el peso actual, si no es sano el objetivo... persuadir al usuario
#http://www.imss.gob.mx/sites/all/statics/salud/tablas_imc/mujeres_imc.pdf  Mujer
#http://www.imss.gob.mx/sites/all/statics/salud/tablas_imc/hombres_imc.pdf   Hombre

#validar si el nombre es de mujer o de hombre
#https://www.buenosaires.gob.ar/areas/registrocivil/nombres/busqueda/buscador_nombres.php?nombre=&sexo=F&Buscar_bt=Buscar&buscar=1
#from genderize import Genderize

#validar el tratamiento de la persona (mujer- 9kg , hombre-12kg)

