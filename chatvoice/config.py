CONFIG={}

def set_config(**args):
    global CONFIG
    CONFIG=args

def get_config():
    global CONFIG
    return CONFIG
