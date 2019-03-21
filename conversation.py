#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import yaml
import os.path
import re
import time
from collections import OrderedDict
from socketIO_client import SocketIO, BaseNamespace
import json


#local imports
from colors import bcolors
from audio import tts_google, tts_local, pull_latest, sr_google, audio_state, start_listening, stop_listening, audio_connect

# Import plugins
# TODO make a better system for plugins
from plugins import random_greeting
# TODO make a better system for filters
from filters import *

re_conditional = re.compile("if (?P<conditional>.*) (?P<cmd>(solve|say|input|loop_slots).*)")
re_while = re.compile("while (?P<conditional>.*) (?P<cmd>(solve|say|input|loop_slots).*)")
re_input = re.compile(r"input (?P<id>[^ ]+)(?: *\| *(?P<filter>\w+)(?P<args>.*)?$)?")
re_set = re.compile(r"set_slot (?P<id>[^ ]+) +(?P<val>.*)$")


class StateNamespace(BaseNamespace):
    pass

class Conversation:
    def __init__(self, filename, name="SYSTEM", verbose=False, tts='google', rec_voice=False, host=None, port=None, samplerate=16000, device=0, channels=1):
        """ Creates a conversation from a file"""

        #Variables
        self.verbose_ = verbose
        self.path = os.path.dirname(filename)
        self.basename = os.path.basename(filename)
        self.modulename = os.path.splitext(self.basename)[0]
        self.strategies = {}
        self.contexts = {}
        self.package = ".".join(['plugins'])
        self.script = []
        self.slots = OrderedDict()
        self.history = []
        self.name = name
        self.channels = channels
        self.tts = tts
        self.pause = False
        self.host = host
        self.port = port
        self.kbfilename = None
        self.kb={}
        self.rec_voice = rec_voice

        with open(filename, 'r') as stream:
            try:
                definition=yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.load_conversation(definition)
        self.thread = None
        self.samplerate = samplerate
        self.device = device

    def set_thread(self,thread):
        self.thread = thread

    def set_sid(self,sid):
        self.sid = sid

    def start(self):
        time.sleep(0.8)
        if self.thread:
            self.thread.start()

    def pause(self):
        self.pause=True

    def update_(self,conversation):
        self.contexts[conversation.modulename]=conversation
        self.strategies.update(conversation.strategies)
        self.verbose(bcolors.OKBLUE,"Setting conversation",conversation.modulename,bcolors.ENDC)

    def _load_conversations(self,conversations,path="./"):
        for conversation in conversations:
            conversation=os.path.join(path,conversation)
            self.verbose(bcolors.OKGREEN,"Loading conversation",conversation,bcolors.ENDC)
            conversation_=Conversation(filename=conversation)
            self.update_(conversation_)

    def _load_plugings(self,plugins_):
        for plugin in plugins_:
            self.verbose(bcolors.OKGREEN,"Importing plugin",plugin,bcolors.ENDC)

    def _load_strategies(self,strategies):
        for strategy,script in strategies.items():
            self.verbose(bcolors.OKBLUE,"Setting strategy",strategy,bcolors.ENDC)
            self.strategies[strategy]=script

    def _load_dbs(self,dbs,path="."):
        for dbname,loading_script in dbs.items():
            loading_script=loading_script.strip()
            self.verbose(bcolors.OKBLUE,"Creating db",dbname,bcolors.ENDC)
            if loading_script.startswith("import"):
                bits=loading_script.split()
                db=[]
                if bits[0] == 'import_csv':
                    import csv
                    dbfile=os.path.join(path,bits[1])
                    self.verbose(bcolors.OKBLUE,"Loading csv",dbfile,bcolors.ENDC)
                    with open(dbfile) as csv_file:
                        csv_reader = csv.reader(csv_file, delimiter=',')
                        line_count = 0
                        for row in csv_reader:
                            if line_count == 0:
                                self.verbose(bcolors.OKBLUE,"Column names are "," ".join(row),dbname,bcolors.ENDC)
                                line_count += 1
                            else:
                                line_count += 1
                                db.append(row)
            try:
                self.slots['db'][dbname]=db
            except KeyError:
                self.slots['db']={}
                self.slots['db'][dbname]=db


    def _load_kb(self,kbname,path="."):
        jsonfile=os.path.join(path,kbname)
        self.verbose(bcolors.OKBLUE,"Loading kb",bcolors.ENDC)
        self.verbose(bcolors.OKBLUE,"Loading json",jsonfile,bcolors.ENDC)
        try:
            with open(jsonfile) as json_file:
                kb = json.load(json_file)
        except FileNotFoundError:
            kb={}
        for slotname,slotvalue in kb.items():
            self.slots[slotname]=slotvalue
        self.kbfilename=jsonfile

    def _load_slots(self,slots):
        for slot in slots:
            self.slots[slot]=None

    def _load_settings(self,settings):
        try:
            self.name=settings['name']
        except KeyError:
            pass

    def load_conversation(self,definition):
        """ Loads a full conversation"""
        try:
            self._load_conversations(definition['conversations'],path=self.path)
        except KeyError:
            pass
        try:
            self._load_slots(definition['slots'])
        except KeyError:
            pass

        # TODO: a better pluggin system
        try:
            self._load_plugings(definition['plugins'])
        except KeyError:
            pass
        try:
            self._load_strategies(definition['strategies'])
        except KeyError:
            pass
        try:
            self._load_dbs(definition['dbs'],path=self.path)
        except KeyError:
            pass
        try:
            self._load_kb(definition['kb'],path=self.path)
        except KeyError:
            pass
        try:
            self._load_settings(definition['settings'])
        except KeyError:
            pass

        self.script=definition['script']

    def verbose(self,*args):
        """ Prints message in verbose mode """
        if self.verbose_:
            print(*args)

    def add_turn(self,user,cmds):
        self.history.append((user,cmds))

    def solve_(self,*args):
        """ Command solve to look for an specific strategy """
        if len(args)!=1:
            raise ArgumentError('Expected an argument but given more or less')
        self.verbose(bcolors.WARNING,"Trying to solve",args[0])
        try:
            if args[0] in self.contexts:
                self.current_context=self.contexts[args[0]]
                slots_tmp=OrderedDict(self.current_context.slots)
                slots_tmp_ = self.slots
                self.slots=self.current_context.slots
                self.slots.update(slots_tmp_)
                self.execute_(self.current_context.script)
                self.current_context.slots=slots_tmp
                self.current_context=self
            elif args[0] in self.strategies:
                self.execute_(self.strategies[args[0]])
            else:
                raise KeyError('The solving strategy was not found', args[0])
        except KeyError:
            raise KeyError('The solving strategy was not found',args[0])


    def eval_(self,cmd):
        """ evaluate python expression"""
        result=eval(cmd,globals(),self.slots)
        if result:
            self.execute_line_(result)
        else:
            pass

    def execute__(self,cmd):
        """ execute python command"""
        print("CMD",cmd)
        exec(cmd)


    def say_(self,cmd):
        """ Say command """

        result=eval(cmd,globals(),self.slots)
        if self.tts=='google':
            stop_listening()
            tts_google(result)
            start_listening()
        elif self.tts=='local':
            stop_listening()
            tts_local(result)
            start_listening()
        else:
            pass
        MSG="{}: {}".format(self.name, result)
        if self.host:
            self.socket_state.emit('say',{"msg":MSG})
        else:
            print(MSG)


    def input_(self,line):
        """ Input command """
        m=re_input.match(line)

        if m:
            print("USER: ",end='')
            if self.rec_voice:
                start_listening()
                filename=None
                while not filename:
                    time.sleep(0.1)
                    filename=pull_latest()

                result=sr_google(filename)
                print("{} [{}]".format(result,filename))
            else:
                result=input()

            idd=m.group('id')
            raw=result
            if m.group('filter'):
                fil=m.group('filter')
                args=m.group('args').split()
                slots_ = dict(self.slots)
                slots_['args']=args
                result=eval('{}("{}",*args)'.format(fil,result),globals(),slots_)
            if self.host:
                self.socket_state.emit('input',{"msg":"USER: {}/{}".format(result,raw)})
            self.slots[idd]=result

    def loop_slots_(self):
        """ Loop slots until fill """
        for slot in [name for name, val in self.slots.items() if val is None]:
            self.execute_line_("solve {}".format(slot))

    def conditional_(self,line):
        """ conditional execution """
        m=re_conditional.match(line)
        if m:
            conditional=m.group('conditional')
            cmd=m.group('cmd')
            try:
                result=eval(conditional,globals(),self.slots)
            except NameError:
                print(bcolors.WARNING, "False because variable not defined",bcolors.ENDC)
                result=True
            if result:
                self.execute_line_(cmd)

    def while_(self,line):
        """ while execution """
        m=re_while.match(line)
        if m:
            conditional=m.group('conditional')
            cmd=m.group('cmd')
            try:
                result=eval(conditional,globals(),self.slots)
            except NameError:
                print(bcolors.WARNING, "False because variable not defined",bcolors.ENDC)
                result=True
            if result:
                self.execute_line_(cmd)
                self.execute_line_(line)

    def add_slot_(self,arg):
        self.slots[arg]=None

    def set_slot_(self,line):
        m=re_set.match(line)
        if m:
            cmd="self.slots['{}']={}".format(m.group('id'),m.group('val'))
            exec(cmd)

    def del_slot_(self,arg):
        del self.slots[arg]

    def remember_(self,arg):
        self.kb[arg]=self.slots[arg]
        with open(self.kbfilename,"w") as json_file:
            json.dump(self.kb,json_file)

    def empty_slot_(self,line):
        self.slots[line]=None

    def execute_line_(self,line):
        line=line.strip()
        self.verbose(bcolors.WARNING,"Command",line,bcolors.ENDC)
        if self.slots:
            self.verbose(bcolors.OKGREEN, "SLOTS:", ", ".join(["{}:{}".format(x,y)
                                                                for x,y in self.slots.items()]), bcolors.ENDC)
        if line.startswith('solve '):
            cmd,args=line.split(maxsplit=1)
            self.solve_(*args.split())
        elif line.startswith('execute '):
            cmd,args=line.split(maxsplit=1)
            self.execute__(args)
        elif line.startswith('say '):
            cmd,args=line.split(maxsplit=1)
            self.say_(args)
        elif line.startswith('input '):
            self.input_(line)
        elif line.startswith('loop_slots'):
            self.loop_slots_()
        elif line.startswith('if '):
            self.conditional_(line)
        elif line.startswith('while '):
            self.while_(line)
        elif line.startswith('add_slot'):
            cmd,args=line.split(maxsplit=1)
            self.add_slot_(args)
        elif line.startswith('empty_slot '):
            cmd,args=line.split(maxsplit=1)
            self.empty_slot_(args)
        elif line.startswith('set_slot '):
            self.set_slot_(line)
        elif line.startswith('del_slot '):
            cmd,args=line.split(maxsplit=1)
            self.del_slot_(args)
        elif line.startswith('remember '):
            cmd,args=line.split(maxsplit=1)
            self.remember_(args)
        else:
            self.eval_(line)

    def execute_(self,script):
        for line in script:
            if not self.pause:
                self.execute_line_(line)
            else:
                time.sleep(0.1)

    def execute(self):
        if self.host:
            self.socket = SocketIO(self.host,self.port)
            self.socket_state = self.socket.define(StateNamespace, '/state')
        audio_connect(samplerate=self.samplerate,device=self.device, host=self.host, port=self.port, activate = self.rec_voice, channels = self.channels)
        self.current_context=self
        self.execute_(self.script)

