#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse
from transformers import pipeline

if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
    p.add_argument("Model",
            help="Model directory")
    p.add_argument("S",
            help="Sentence to parse")
    p.add_argument("-v", "--verbose",
            action="store_true",
            help="Verbose mode [%(default)s]")

    args = p.parse_args()


    # Allocate a pipeline for sentiment-analysis
    nlp = pipeline('ner',args.Model)
    print(nlp(args.S))
