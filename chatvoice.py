#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse


# local imports
import conversation


if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
    p.add_argument("CONV",
            help="Conversation file")
    p.add_argument("-v", "--verbose",
            action="store_true", dest="verbose",
            help="Verbose mode [Off]")

    args = p.parse_args()
   
    conversation = conversation.Conversation(filename=args.CONV)
    conversation.execute()

    print("Summary values:")
    for val,k in conversation.slots.items():
        print(val,k)
