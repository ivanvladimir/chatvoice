#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import argparse
import jsonlines
import random
import os.path

def sntcsntc2colums(sntc,default_label="O"):
    segments=[]
    lines=[]
    prev_fin=0
    labels=sorted(sntc['labels'],key=lambda x: x[0])
    for ini,fin,label in labels:
        segments.append((sntc['text'][prev_fin:ini],default_label))
        segments.append((sntc['text'][ini:fin],label))
        prev_fin=fin
    segments.append((sntc['text'][prev_fin:],default_label))

    for segment,label in segments:
        if len(segment)==0:
            continue
        for i,w in enumerate(segment.split()):
            if label==default_label:
                lines.append((f'{w}',f'{label}'))
            else:
                if i==0:
                    lines.append((f'{w}', f'B-{label}'))
                    fst=False
                else:
                    lines.append((f'{w}', f'I-{label}'))
    return lines


if __name__ == '__main__':
    p = argparse.ArgumentParser("chatvoice")
    p.add_argument("JSON",
            help="Json file")
    p.add_argument("-odir",default='data',
            help="Outpur directory")
    p.add_argument("-v", "--verbose",
            action="store_true",
            help="Verbose mode [%(default)s]")

    args = p.parse_args()

    data=[]
    with jsonlines.open(args.JSON) as reader:
        for i,sntc in enumerate(reader):
            data.append(sntcsntc2colums(sntc))


    random.shuffle(data)
    partitions=[
            ('train.txt',data[:int(0.8*len(data))]),
            ('dev.txt',data[int(0.8*len(data)):int(0.9*len(data))]),
            ('test.txt',data[int(0.9*len(data)):])]

    for name,data in partitions:
        with  open(os.path.join(args.odir,name),'w') as fd:
            for i,lines in enumerate(data):
                if i >0:
                    print(file=fd)
                for word,label in lines:
                    print(f'{word} {label}',file=fd)
