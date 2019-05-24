import json
#conexion con la base de datos del usuario
with open('/home/pi/chatvoice/conversations/kb.db','r') as f:
    data =f.readlines()

for x in data:
    json.dumps(x)
y = json.loads(x)


def remember_name(var):
    nombre = var
    msg = y["name"]
    return 'set_slot {0} "{1}"'.format(nombre,str(msg))

f.close()
