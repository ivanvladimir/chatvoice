import yaml
import sys
import os

from sqlalchemy import select

from ..models import KB
from .db.database_sync import get_db_ctx 
from .logger import get_logger

log = get_logger(__name__)

class Conversation:
    def __init__(self, project_pathname: str, user_id: int, filename: str = "main.yaml", settings: dict = {}, slots: dict = {}):
        self.project_pathname = project_pathname
        self.stacks_ : list[list] = []
        self.commands : list[str] = []
        self.strategies : dict = {}
        self.templates : dict = {}
        self.prompts: dict = {}
        self._restricted_locals : dict = {}
        self.conversations : dict = {}
        self.slots : dict = {}
        self.return_ : dict = {}
        self.user_id = user_id
        self.name = os.path.splitext(filename)[-2]
        self._load_conversation(project_pathname, filename, settings, slots)
 
    def _load_conversation(self, project_pathname: str, filename: str = "main.yaml", settings_: dict = {}, slots_ : dict = {}):
        log.info(f"Starting loading conversation from: {project_pathname}")
        filename = os.path.join(project_pathname,filename) 
        with open(filename, "r", encoding="utf-8") as stream:
            try:
                definition = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                self.console.print(exc)
                log.error(f"Error while reading: {filename}")
                sys.exit()

        slots = definition.get("slots",{})
        slots.update(slots_)
        slots.update({"_settings":settings_})
        self.load_slots(slots, filename.endswith('main.yaml'))

        settings= definition.get("settings",{})
        settings.update(settings_)
        self.load_settings(settings)
        
        self.commands = list(definition.get("script",{}))
        self.load_strategies(definition.get("strategies",{}))
        self.load_templates(definition.get("templates",{}))
        self.load_prompts(definition.get("prompts",{}))

        self.plugins = self.load_plugins(definition.get("plugins",{}))

        self.load_conversations(definition.get("conversations",{}),settings=self.settings)
        
        log.info(f"Finishing loading conversation from: {filename}")

    def load_templates(self, templates={}, path="resources"):
        for template in templates:
            template = os.path.join(self.project_pathname,path,template)
            log.info(f"Starting loading templates from: {template}")
            with open(template, "r", encoding="utf-8") as stream:
                try:
                    template_ = yaml.safe_load(stream)
                    for k in template_.keys():
                        if k in self.templates:
                            log.error(f"Template {k} already defined")
                    self.templates.update(template_)
                except yaml.YAMLError:
                    log.error(f"Error while reading: {template}, definitions being ignored")
                    log.error(exec)
                    sys.exit()

    def load_prompts(self, prompts={}, path="resources"):
        for prompts_ in prompts:
            prompts_ = os.path.join(self.project_pathname,path,prompts_)
            with open(prompts_, "r", encoding="utf-8") as stream:
                try:
                    prompts_ = yaml.safe_load(stream)
                    for k in prompts_.keys():
                        if k in self.prompts:
                            log.error(f"Prompt {k} already defined")
                    self.prompts.update(prompts_)
                except yaml.YAMLError as exc:
                    log.error(f"Error while reading: {prompts}, definitions being ignored [{exc}]")
                    log.error(exec)
                    sys.exit()

    def load_plugins(self, plugins_: dict):
        safe_builtins = {
            'print': print,
            'len': len,
            'range': range,
            'int': int,
            'dict':dict,
            'str': str,
            'list': list}

        restricted_globals = {'__builtins__': safe_builtins}
        restricted_locals = self._restricted_locals
        for filename in plugins_:
            plugin_path = os.path.join(self.project_pathname,"plugins",filename)
            with open(plugin_path, 'r') as f:
                code = f.read()
            compiled_code = compile(code, plugin_path, 'exec')
            exec(compiled_code, restricted_globals, restricted_locals)

    def load_slots(self, slots_: dict, main: bool = True):
        if main:
            with get_db_ctx() as db:
                result = db.execute(
                    select(KB).filter_by(
                        user_id=self.user_id,
                        project_path=str(self.project_pathname),
                        is_deleted=False,
                    )
                )
                kb = result.scalar_one_or_none()
                if kb:
                    self.slots = dict(kb.payload)
                else:
                    self.slots = dict()
        self.slots.update(slots_)

    def load_strategies(self, strategies_: dict):
        self.strategies = {
        }
        self.strategies.update(strategies_)

    def load_conversations(self, conversations_: dict, settings: dict = {} ):
        self.conversations = {
        }
        for filename in conversations_:
            basename = os.path.splitext(os.path.basename(filename))[0]
            if basename not in self.conversations: 
                log.info(f"Loading conversation '{filename}'")
                self.conversations[basename]={'project_pathname':self.project_pathname,
                                              'filename':filename,
                                              'user_id':self.user_id}
            else:
                log.info(f"Conversation '{filename}' already in {self.basename}, it will be ignored")

    def load_settings(self, settings_: dict):
        self.settings = {
            "_name_user":"USER",
            "_name_system":"SYSTEM"
        }
        self.settings.update(settings_)


