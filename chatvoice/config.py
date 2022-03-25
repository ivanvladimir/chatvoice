import json


def set_config(**args):
    with open("/tmp/chatvoice_config.txt", "w") as cc:
        json.dump(args, cc)


def get_config():
    with open("/tmp/chatvoice_config.txt", "r") as cc:
        CONFIG = json.load(cc)
    return CONFIG
