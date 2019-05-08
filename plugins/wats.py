from plugins.prueba2 import procesa_watson
var = ''
procesa_watson("hola")
while var != "adios" :
    var = input('USER: ')
    if var == "comida":
        msg = print ("te recominedo comer...")
    elif var == "cena":
        msg = print ("te recominedo cenar...")
    elif var == "otra cosa":
        msg = print ("Bueno, que te parecería entonces...")
    else:
        msg = print ("no te entendí")
print("adiosito....")
