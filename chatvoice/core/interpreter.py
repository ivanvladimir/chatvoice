from typing import Generator, Any
from datetime import datetime, UTC
from sqlalchemy import update, insert, select
from core.logger import get_logger
from core.db.database_sync import get_db_ctx
from utils.llm import llm_client_response
from models import KB
import ast
import random
from pathlib import Path

from simpleeval import simple_eval, NameNotDefined, InvalidExpression

from .parser import Clause, Condition, parse_line, Command
from .conversation import Conversation

log = get_logger(__name__)


class Interpreter:
    """Runs the execution of commands within a parsed chain."""

    def __init__(self, project_pathname: Path, user_id: int, settings: dict = None, slots: dict = None, llm_client = None):
        self.project_pathname = project_pathname
        
        # Path.stem correctly gets the filename without the extension
        self.name = project_pathname.stem

        self.stack_ = []
        self.conversation = Conversation(
            project_pathname, 
            user_id, 
            settings=settings or {},
            slots=slots or {}
        )
        self.settings: dict = self.conversation.settings
        self.commands = list(self.conversation.commands)
        self.exit = False
        self.error = None
        self.status: dict = {}
        self.llm_client = llm_client

    def run(self, callback, state: dict = None) -> Generator[dict, Any, None]:
        log.info(f"Starting execution of conversation {self.name}")
   
        self.status = {}
        while self.commands and not self.exit:
            line = self.commands.pop(0)
            chain = parse_line(line)
            yield from self._run_chain(chain, callback)
            
            # Handle stack (strategies and sub-conversations)
            if not self.commands and self.stack_:
                obj = self.stack_.pop()
                if len(obj) == 1:  # Strategy
                    self.commands = obj[0]
                    log.info("Resuming after strategy")
                elif len(obj) == 2:  # Conversation
                    old_conversation, commands = obj
                    old_conversation.slots.update(self.conversation.return_)
                    self.conversation, self.commands = old_conversation, commands
                    log.info("Resuming execution of parent conversation")

        if self.error:
            raise self.error

        log.info(f"Finishing execution of conversation {self.name}")
 
    def _run_chain(self, chain, callback) -> Generator[dict, Any, None]:
        """Execute each command in the given chain sequentially."""
        is_continuation = False
        
        while chain.commands and not self.exit:
            c = chain.commands.pop(0)
            
            # Handle shorthand dot-commands (e.g., .my_func -> exec my_func)
            if c.name.startswith("."):
                c = Command(
                    name="exec",
                    _command=c._command,
                    args=[c.name[1:]] + list(c.args),
                    condition=c.condition,
                    condition_type=c.condition_type
                )
            
            # 1. Evaluate 'if ... then' condition if present
            if c.condition is not None and not self._evaluate_condition(c.condition):
                continue  # Condition is False, skip this command
            
            # 2. Dispatch to the correct handler method
            handler = getattr(self, f"_cmd_{c.name}", None)
            if handler:
                yield from handler(c.args, callback, is_continuation)
            else:
                self.exit = True
                self.error = ValueError(f"Unknown command: {c.name}")
                return

            # 3. Check for execution errors
            if self.exit or not self.status.get('ok', False):
                if not self.error:
                    self.error = ValueError(f"Error while evaluating {c._command}")
                return
                
            is_continuation = True
    
    def _evaluate_condition(self, condition: Condition) -> bool:
        """Evaluates a parsed Condition. Returns True if ANY clause is True."""
        for clause in condition.clauses:
            if self._evaluate_clause(clause):
                return True
            if self.exit:
                return False
        return False

    def _evaluate_clause(self, clause: Clause) -> bool:
        """Evaluates a parsed Clause using the conversation's slots."""
        context = self.conversation.slots
        left_val = self._resolve_value(clause.left, context)

        if clause.op is None:
            result = bool(left_val)
        else:
            if clause.right is None:
                self.exit = True
                self.error = ValueError(f"Operator '{clause.op}' requires a right operand.")
                return False
            
            right_val = self._resolve_value(clause.right, context)
            result = self._apply_op(left_val, clause.op, right_val)

            if self.exit:
                return False

        return (not result) if clause.negate else result

    def _resolve_value(self, key: str, context: dict) -> Any:
        """
        Looks up the key in context. If not found, attempts to parse as a literal.
        Falls back to returning the raw string.
        """
        if key in context:
            return context[key]
        try:
            return ast.literal_eval(key)
        except (ValueError, SyntaxError):
            return key

    def _apply_op(self, left: Any, op: str, right: Any) -> bool:
        """Applies the comparison operator, with type coercion for numbers."""
        left, right = self._coerce(left, right)
        
        ops = {
            "==": lambda l, r: l == r,
            "!=": lambda l, r: l != r,
            ">":  lambda l, r: l > r,
            "<":  lambda l, r: l < r,
            ">=": lambda l, r: l >= r,
            "<=": lambda l, r: l <= r,
            "in": lambda l, r: l in r if isinstance(r, (list, str, dict)) else False,
        }

        if op in ops:
            try:
                return ops[op](left, right)
            except TypeError:
                return False
        
        self.exit = True
        self.error = ValueError(f"Unsupported operator: {op}")
        return False

    def _coerce(self, left: Any, right: Any):
        """Ensures numeric strings compare as numbers, not strings."""
        def to_num(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    return float(val)
                except ValueError:
                    return val
            return val

        l_num, r_num = to_num(left), to_num(right)
        
        if isinstance(l_num, float) and isinstance(r_num, float):
            return l_num, r_num
            
        return left, right

    def _cmd_solve(self, args, callback, continuation) -> Generator[dict, Any, None]:
        strategy_name = args[0]
        
        if strategy_name not in self.conversation.strategies and strategy_name not in self.conversation.conversations:
            self.exit = True
            self.error = ValueError(f"Unknown strategy or conversation: {strategy_name}")
            return

        if strategy_name in self.conversation.conversations:
            # Conversation
            self.stack_.append((self.conversation, self.commands))
            conv_args = self.conversation.conversations[strategy_name].copy()
            conv_args['slots'] = dict(self.conversation.slots)
            
            log.info(f"Starting execution of conversation {strategy_name}")
            self.conversation = Conversation(**conv_args)
            self.commands = list(self.conversation.commands)
        else:
            # Strategy
            self.stack_.append((self.commands,))
            self.commands = list(self.conversation.strategies[strategy_name])
            log.info(f"Starting execution of strategy {strategy_name}")
            
        self.status = {'command': 'solve', 'ok': True}
        yield from ()

    def _cmd_return(self, args, callback, continuation) -> Generator[dict, Any, None]:
        slot_name = args[0]
        if slot_name not in self.conversation.slots:
            self.status = {'command': 'return', 'value': slot_name, 'ok': False}
        else:
            self.conversation.return_[slot_name] = self.conversation.slots[slot_name]
            self.status = {
                'command': 'return',
                'variable': slot_name,
                'value': self.conversation.slots[slot_name],
                'ok': True,
            }
        yield from ()

    def _cmd_llm(self, args, callback, continuation) -> Generator[dict, Any, None]:
        key = args[0]
        if key in self.conversation.prompts:
            prompt = self._resolve_prompt(key)
        else:
            try:
                prompt = key.format_map(self.conversation.slots)
            except KeyError:
                prompt = key  # Fallback if slot is missing
        response=llm_client_response(self.llm_client, prompt)
        if len(args)==1:
            self.status = {'command': 'llm', 'value': [response], 'ok': True}
        elif len(args)==2:
            variable = args[1]
            self.conversation.slots[variable]=response
            self.status = {'command': 'llm', 'variable': variable, 'value': [response], 'ok': True}
        yield from ()

    def _cmd_say(self, args, callback, continuation) -> Generator[dict, Any, None]:
        if len(args)==0 and continuation:
            texts=self.status['value']
        elif len(args)==1:
            key = args[0]
            if key in self.conversation.templates:
                texts = self._resolve_template(key)
            else:
                try:
                    text = key.format_map(self.conversation.slots)
                except KeyError:
                    text = key  # Fallback if slot is missing
                texts = [text]
            
            self.status = {'command': 'say', 'value': texts, 'ok': True}
        yield {"cmd": "say", "args": texts}

    def _cmd_listen(self, args, callback, continuation) -> Generator[dict, Any, None]:
        variable = str(args[0])
        yield {"cmd": "listen"}
        user_input = callback()
        self.conversation.slots[variable] = user_input or ""
        self.status = {
            'command': 'listen',
            'value': user_input or "",
            'variable': variable,
            'ok': True,
        }

    def _cmd_set(self, args, callback, continuation) -> Generator[dict, Any, None]:
        if not args:
            self.status = {'command': 'set', 'ok': False}
            yield from ()
            return

        variable = str(args[0])
        if continuation and len(args) == 1:
            value = self.status.get('value')
        else:
            value = args[1:]

        self.conversation.slots[variable] = value
        self.status = {'command': 'set', 'value': value, 'variable': variable, 'ok': True}
        yield from ()

    def _cmd_exec(self, args, callback, continuation) -> Generator[dict, Any, None]:
        if not args:
            self.status = {'command': 'exec', 'ok': False}
            yield from ()
            return

        func_name = args[0]
        
        eval_context = {**self.conversation._restricted_locals, **self.conversation.slots}
        
        try:
            args_ = [simple_eval(arg, names=eval_context) for arg in args[1:]]
        except (NameNotDefined, InvalidExpression) as e:
            self.exit = True
            self.error = ValueError(f"Exec argument evaluation failed: {e}")
            self.status = {'command': 'exec', 'ok': False}
            yield from ()
            return

        if continuation:
            args_.append(self.status.get("value"))
        
        if func_name not in eval_context:
            self.exit = True
            self.error = ValueError(f"Exec function '{func_name}' is not defined.")
            self.status = {'command': 'exec', 'ok': False}
            yield from ()
            return

        try:
            output = eval_context[func_name](*args_)
            self.status = {'command': 'exec', 'value': output, 'ok': True}
        except Exception as e:
            self.exit = True
            self.error = ValueError(f"Exec function '{func_name}' crashed: {e}")
            self.status = {'command': 'exec', 'ok': False}
            
        yield from ()

    def _cmd_remember(self, args, callback, continuation) -> Generator[dict, Any, None]:
        if len(args) >= 2:
            variable, value = str(args[0]), args[1]
        elif len(args) == 1:
            variable = str(args[0])
            value = self.status.get('value') if continuation else None
        else:
            variable = self.status.get('variable')
            value = self.status.get('value')

        if not variable or value is None:
            self.status = {'command': 'remember', 'ok': False}
            yield from ()
            return

        self.conversation.slots[variable] = value
        
        with get_db_ctx() as db:
            result = db.execute(
                select(KB).filter_by(
                    user_id=self.conversation.user_id,
                    project_path=str(self.conversation.project_pathname),
                )
            )
            kb = result.scalar_one_or_none()
            
            if not kb:
                stmt = insert(KB).values(
                    user_id=self.conversation.user_id,
                    project_path=str(self.conversation.project_pathname),
                    payload={variable: value},
                    created_at=datetime.now(UTC),
                )
                db.execute(stmt)
            else:
                payload = dict(kb.payload)
                payload.update({variable: value})
                stmt = (
                    update(KB)
                    .where(KB.id == kb.id)
                    .values(payload=payload, updated_at=datetime.now(UTC))
                )
                db.execute(stmt)
            db.flush()
            
        self.status = {'command': 'remember', 'value': value, 'variable': variable, 'ok': True}
        yield from ()

    def _cmd_info(self, args, callback, continuation) -> Generator[dict, Any, None]:
        info_data = []
        for info_type in args:
            info_type=info_type.replace(",","")
            if info_type == "slots":
                info_data.append(('slots', self.conversation.slots))
            elif info_type == "name":
                info_data.append(('name', self.name))
            elif info_type == "status":
                info_data.append(('status', self.status))
                
        self.status = {
            'command': 'info',
            'value': info_data[-1] if info_data else [],
            'ok': bool(info_data), # False if no valid args were passed
        }

        yield {"cmd": "info", "args": info_data}

    def _resolve_template(self, name):
        t = self.conversation.templates[name]
        eval_context = {**self.conversation._restricted_locals, **self.conversation.slots}
        
        try:
            if 'CASES' in t:
                val = simple_eval(t['SLOT'], names=eval_context)
                for case in t['CASES']:
                    if val in case['VALS']:
                        res = random.choice(case['MSGS'])
                        break
                else:
                    res = random.choice(t['CASES'][-1]['MSGS']) # Fallback to last case
            else:
                res = random.choice(t)
                
            # Build f-strings dynamically and evaluate them
            fmt_strings = []
            for m in res['MSG']:
                text = m["TEXT"].strip()
                if '\n' in text:
                    fmt_strings.append(f'f"""{text}"""')
                else:
                    fmt_strings.append(f'f"{text}"')
                    
            return [simple_eval(s, names=eval_context) for s in fmt_strings]
            
        except (NameNotDefined, InvalidExpression, KeyError) as e:
            log.error(f"Failed to resolve template {name}: {e}")
            return [f"[Error resolving template {name}]"]

    def _resolve_prompt(self, name):
        p = self.conversation.prompts[name]
        eval_context = {**self.conversation._restricted_locals, **self.conversation.slots}
        
        text = p.strip()
        fmt_str = f'f"""{text}"""' if '\n' in text else f'f"{text}"'
        
        try:
            return simple_eval(fmt_str, names=eval_context)
        except (NameNotDefined, InvalidExpression) as e:
            log.error(f"Failed to resolve prompt {name}: {e}")
            return text
