CONFIG={}

def set_config(**args):
    global CONFIG
    CONFIG=args
    print("SET",CONFIG)

def get_config():
    global CONFIG
    print("GET",CONFIG)
    return CONFIG
