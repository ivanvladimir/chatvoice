import random
import json


def conversacion_diaria(*args)

	var=args[0] 

	if prueba2.procesa_watson(var) == "pedir_comida":
	    #dar recomendacion de comida
	    #msg = sugerencia("comida")
	elif prueba2.procesa_watson(var) == "pedir_desayuno":
	    #dar recomendacion de desayuno
            #msg = sugerencia("desayuno")
	else prueba2.procesa_watson(var) == "pedir_cena":
	    #dar recomendacion de cena
	    #msg = sugerencia("cena")
	else prueba2.procesa_watson(var) == "peticion_colacion":
	    #dar recomendacion de colacion
	    #msg = sugerencia("colacion")
	else prueba2.procesa_watson(var) == "chequeo_peso":
	    #
	    #msg =
	else prueba2.procesa_watson(var) == "monitoreo":
	    #
	    #msg =
	else prueba2.procesa_watson(var) == "#dudas_de_bella":
	    #
	    #msg =
	else prueba2.procesa_watson(var) == "#dudas_de_dieta":
	    #
            #msg =
	else:
		# "Disculpa. No te entendí"
return 'set_slot {0} "{1}"'.format(var,msg)
