#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Ivan Vladimir Meza Ruiz 2018
# GPL 3.0

# imports
import yaml
import os.path
import re
from collections import OrderedDict

#local imports
from colors import bcolors
from audio import tts_google, tts_local, pull_latest, sr_google

# Import plugins
# TODO make a better system for plugins
from plugins import random_greeting
# TODO make a better system for filters
from filters import *

re_conditional = re.compile("if (?P<conditional>.*) (?P<cmd>(solve|say|input|loop_slots).*)")
re_while = re.compile("while (?P<conditional>.*) (?P<cmd>(solve|say|input|loop_slots).*)")
re_input = re.compile(r"input (?P<id>[^ ]+)(?: *\| *(?P<filter>.*))?")
re_set = re.compile(r"set_slot (?P<id>[^ ]+) +(?P<val>.*)$")

class Conversation:
    def __init__(self, filename, name="SYSTEM",verbose=False, tts='google', rec_voice=False):
        """ Creates a conversation from a file"""
        # Variables 
        self.verbose_=verbose
        self.path=os.path.dirname(filename)
        self.basename=os.path.basename(filename)
        self.modulename=os.path.splitext(self.basename)[0]
        self.strategies={}
        self.contexts={}
        self.package = ".".join(['plugins'])
        self.script=[]
        self.slots=OrderedDict()
        self.history=[]
        self.name=name
        self.tts=tts
        self.rec_voice=rec_voice

        with open(filename, 'r') as stream:
            try:
                definition=yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.load_conversation(definition)

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
        #try:
        #    self._load_plugings(definition['plugins'])
        #except KeyError:
        #    pass
        try:
            self._load_strategies(definition['strategies'])
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
        result=eval(cmd)
        self.execute_line_(result)

    def execute__(self,cmd):
        """ execute python command"""
        print("CMD",cmd)
        exec(cmd)


    def say_(self,cmd):
        """ Say command """

        result=eval(cmd,globals(),self.slots)
        if self.tts=='google':
            tts_google(result)
        elif self.tts=='local':
            tts_local(result)
        else:
            pass
        print("{}:".format(self.name), result)


    def input_(self,line):
        """ Input command """
        m=re_input.match(line)
            
        if m:
            print("USER: ",end='')
            if self.rec_voice:
                filename=pull_latest()
                result=sr_google(filename)
                print(result)
            else:
                result=input()

            idd=m.group('id')
            if m.group('filter'):
                fil=m.group('filter')
                result=eval('{}("{}")'.format(fil,result),globals(),self.slots)

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
        else:
            self.eval_(line)


    def execute_(self,script):
        for line in script:
            self.execute_line_(line)
           
    def execute(self):
        self.current_context=self
        self.execute_(self.script)
