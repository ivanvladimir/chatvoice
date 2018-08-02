import re

def leftNumber(word,slot):
    word=re.sub("[^0-9]", "",word)
    return 'set_slot '+str(slot)+' "'+str(word)+'"'

def say(*args):
    cadena = ""
    for a in args:
        cadena=cadena+" "+a

    return 'say "'+str(cadena)+'"'


