import json 
from genderize import Genderize


with open('/home/ljanine/repo/chatvoice/conversations/kb.db','r') as f:
    data =f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)


def val(*args):
    var=args[0]


    #CALCULA CATEGORIA SEGÚN IMC


    def IMC(classification):
        if (classification<18.5):
            low_weight="Peso bajo"
            classification=low_weight
        elif (classification<24.9):
            normal_weight="Normal"
            classification=normal_weight
        elif (classification<29.9):
            overweight="Sobrepeso"
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




    #VALIDACIÓN DEL PESO OBJETIVO PARA MUJERES

    if (gender == 'female'):
        if (weight_ini>weight_goal):
            if ((weight_ini-weight_goal)<=9):
                if (IMC(IMC_goal)=="Peso bajo"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'Con respecto a tu peso, éste ya es muy bajo. No necesitamos ser delgados para ser perfectos, solo se necesitamos mostrar una hermosa sonrisa'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = 'Peroooo el objetivo que nos propusimos no es sano. Yo te recomiendo que deberías acudir con un nutriologo ' 


                if (IMC(IMC_goal)=="Normal"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'Es bueno mencionarte que ya te encuentras en un estado nutricional normal de acuerdo a tu peso y siguiendo esta dieta aún estarás en el mismo estado pero con menos kilos :) . ¡ánimo Cuais!'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = '!Nuestro objetivo sí que se puede cumplir!'

                if (IMC(IMC_goal)=="Sobrepeso") or (IMC(IMC_goal)=="Obesidad I") or (IMC(IMC_goal)=="Obesidad II") or (IMC(IMC_goal)=="Obesidad III"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'No se trata de dónde estés, sino a dónde quieres llegar. Por algo se empieza'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = 'Vale, vale. Si podemos cumplir el objetivo'


            else:
                print("Ingrese nuevamente")



    #VALIDACIÓN DEL PESO OBJETIVO PARA HOMBRES

    if (gender == 'male'):
        if (weight_ini>weight_goal):
            if ((weight_ini-weight_goal)<=12):
                if (IMC(IMC_goal)=="Peso bajo"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'Con respecto a tu peso, éste ya es muy bajo. Yo te recomiendo que deberías acudir con un nutriologo'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = 'El objetivo que nos propusimos no es sano. No necesitamos ser delgados para ser perfectos, solo se necesitamos mostrar una hermosa sonrisa' 


                if (IMC(IMC_goal)=="Normal"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'Ya te encuentras en un estado nutricional normal de acuerdo a tu peso y siguiendo esta dieta aún estarás en el mismo estado pero con menos kilos :) . ¡ánimo Cuais!'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = '!Nuestro objetivo sí que se puede cumplir!'

                if (IMC(IMC_goal)=="Sobrepeso") or (IMC(IMC_goal)=="Obesidad I") or (IMC(IMC_goal)=="Obesidad II") or (IMC(IMC_goal)=="Obesidad III"):
                    if(IMC(IMC_goal)==IMC(IMC_ini)):
                        msg = 'No se trata de dónde estés, sino a dónde quieres llegar. Por algo se empieza'
                    if(IMC(IMC_goal)!=IMC(IMC_ini)):
                        msg = 'Vale, vale. Si podemos cumplir el objetivo'

            else:
                print("Ingrese nuevamente")


    return 'set_slot {0} "{1}"'.format(var,msg)

f.close()





#Validar el peso objetivo con el peso actual, si no es sano el objetivo... persuadir al usuario                                                 ¡LISTO!
#http://www.imss.gob.mx/sites/all/statics/salud/tablas_imc/mujeres_imc.pdf  Mujer
#http://www.imss.gob.mx/sites/all/statics/salud/tablas_imc/hombres_imc.pdf   Hombre

#validar si el nombre es de mujer o de hombre                                                                                                   ¡LISTO!
#https://www.buenosaires.gob.ar/areas/registrocivil/nombres/busqueda/buscador_nombres.php?nombre=&sexo=F&Buscar_bt=Buscar&buscar=1              

#from genderize import Genderize

#validar el tratamiento de la persona (mujer- 9kg , hombre-12kg)                                                                                ¡LISTO!
