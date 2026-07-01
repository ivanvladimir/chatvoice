from typing import Generator, Any
from datetime import datetime, UTC
from sqlalchemy import update, insert, select
from core.logger import get_logger
from core.db.database_sync import get_db_ctx
from models import KB
import ast
import os
from pathlib import Path

from .parser import Clause, Condition, parse_line
from .conversation import Conversation

log = get_logger(__name__)


class Interpreter:
    """Runs the execution of commands within a parsed chain."""

    def __init__(self, project_pathname: Path, user_id: int, settings: dict = {}, slots: dict = {}):
        self.project_pathname = project_pathname
        self.basename = os.path.basename(project_pathname)
        if  not project_pathname.suffix: 
            self.name = self.basename
        else:
            self.name = os.path.splitext(self.basename)[-1]

        self.stack_ = []
        self.conversation = Conversation(project_pathname, user_id, settings=settings, slots=slots)
        self.settings: dict = self.conversation.settings
        self.commands = list(self.conversation.commands)
        self.exit = False
        self.error = None
        self.status: dict = {}

    def run(self, callback, state: dict = {}):
        log.info(f"Starting execution of conversation {self.name}")
   
        while len(self.commands) > 0 and not self.exit:
            line = self.commands.pop(0)
            chain = parse_line(line)
            yield from self._run_chain(chain, callback)
            if len(self.commands) == 0 and len(self.stack_):
                obj = self.stack_.pop()
                if len(obj)==1: # strategy
                    self.commands=obj[0]
                    log.info(f"Finishing strategy")
                elif len(obj)==2: # Conversation
                    conversation, commands=obj
                    conversation.slots.update(self.conversation.return_)
                    self.conversation, self.commands= conversation, commands
                    log.info(f"Finishing execuetion of conversation")

        if self.error is not None:
            raise self.error

        log.info(f"Finishing execution of conversation {self.name}")
 

    def _run_chain(self, chain, callback) -> Generator[dict, Any, None]:
        """Execute each command in the given chain sequentially."""
        self.status = {}
        while len(chain.commands) > 0 and not self.exit:
            c = chain.commands.pop(0)
            # 1. Evaluate 'if ... then' condition if present
            if c.condition is not None:
                if not self._evaluate_condition(c.condition):
                    continue # Condition is False, skip this command
            
            # 2. Dispatch to the correct handler method
            handler = getattr(self, f"_cmd_{c.name}", None)
            if handler:
                # All handlers are generators, so yield from them safely
                yield from handler(c.args, callback)
            else:
                self.exit = True
                self.error = ValueError(f"Unknown command: {c.name}")
                return

            # 3. Check for execution errors
            if self.exit:
                return
            if not self.status.get('ok', False):
                self.exit = True
                self.error = ValueError(f"Error while evaluating {c._command}")
                return
    
    def _evaluate_condition(self, condition: Condition) -> bool:
        """
        Evaluates a parsed Condition (one or more OR-joined Clauses).
        Returns True if ANY of the clauses evaluate to True.
        """
        for clause in condition.clauses:
            if self._evaluate_clause(clause):
                return True
            
            # If evaluate_clause encountered an error (e.g., missing right operand), 
            # self.exit will be True. We should stop evaluating immediately.
            if self.exit:
                return False
                
        return False


    def _evaluate_clause(self, clause: Clause) -> bool:
        """
        Evaluates a parsed Clause using the conversation's slots.
        """
        context = self.conversation.slots
        
        # Resolve the left operand
        left_val = self._resolve_value(clause.left, context)

        # If no operator is provided, evaluate the truthiness of the left value
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

        # Apply negation
        return (not result) if clause.negate else result

    def _resolve_value(self, key: str, context: dict) -> Any:
        """
        Looks up the key in the context (slots). 
        If not found, attempts to parse it as a literal (True, 1, 'string', etc.).
        Falls back to returning the raw string.
        """
        if key in context:
            return context[key]
        try:
            return ast.literal_eval(key)
        except ValueError:
            return False
        except SyntaxError:
            return key

    def _apply_op(self, left: Any, op: str, right: Any) -> bool:
        """Applies the comparison operator, with type coercion for numbers."""
        left, right = self._coerce(left, right)
        
        if op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        elif op == "<=":
            return left <= right
        elif op == "in":
            try:
                return left in right
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

        l_num = to_num(left)
        r_num = to_num(right)
        
        if isinstance(l_num, float) and isinstance(r_num, float):
            return l_num, r_num
            
        return left, right

    def _cmd_solve(self, args, callback):
        strategy_name = args[0]
        if strategy_name not in self.conversation.strategies:
            if strategy_name not in self.conversation.conversations:
                self.exit = True
                self.error = ValueError(f"Unknown strategy {strategy_name}")
                return
            else:
                # Conversation
                self.stack_.append((self.conversation, self.commands))
                args=self.conversation.conversations[strategy_name]
                args['slots']=dict(self.conversation.slots)
                log.info(f"Starting execution of conversation {strategy_name}")
                new_conversation=Conversation(**args)
                self.conversation=new_conversation
                self.commands=list(new_conversation.commands)
                self.status = {
                    'command': 'solve',
                    'ok': True,
                }
        else:
            # Strategy
            log.info(f"Starting execution of conversation {self.name}")
            self.stack_.append((self.commands,))
            self.commands = list(self.conversation.strategies[strategy_name])
            log.info(f"Starting execution of strategy {strategy_name}")
            self.status = {
                'command': 'solve',
                'ok': True,
            }
        yield from ()

    def _cmd_return(self, args, callback) -> Generator[dict, Any, None]:
        slot_name=args[0]
        if not slot_name in self.conversation.slots:
            self.status = {
                'command': 'return',
                'value': slot_name,
                'ok': False,
            }
            yield from ()
        else:
            self.conversation.return_[slot_name]=self.conversation.slots[slot_name]
            self.status = {
                'command': 'say',
                'variable': slot_name,
                'value': self.conversation.slots[slot_name],
                'ok': True,
            }
            yield from ()

    def _cmd_say(self, args, callback) -> Generator[dict, Any, None]:
        text = str(args[0]).format_map(self.conversation.slots)
        self.status = {
            'command': 'say',
            'value': [text],
            'ok': True,
        }
        yield {"cmd": "say", "args": [text]}

    def _cmd_listen(self, args, callback) -> Generator[dict, Any, None]:
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

    def _cmd_remember(self, args, callback):
        if len(args) == 1:
            variable = str(c.args[0])
        elif len(args) == 0:
            variable = self.status['variable']
            value = self.status['value']
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
                stmt = update(KB).where(
                    KB.id == kb.id,
                ).values(
                    payload=payload,
                    updated_at=datetime.now(UTC),
                )
                db.execute(stmt)
            db.flush()
        self.status = {
            'command': 'remember',
            'value': value,
            'variable': variable,
            'ok': True,
        }
        yield from ()

    def _cmd_info(self, args, callback):
        if len(args) == 0:
            self.status = {
                'command': 'info',
                'ok': False,
            }
            yield {"cmd": "info", "args": {}}
        args_=[]
        for  info_type in args:
            if info_type.startswith("slots"):
                args_.append(('slots',self.conversation.slots))
            if info_type.startswith("name"):
                args_.append(('name', self.name))
        self.status = {
            'command': 'info',
            'value': args_[-1] if len(args_) else [],
            'ok': True,
        }

        yield {"cmd": "info", "args": args_}




