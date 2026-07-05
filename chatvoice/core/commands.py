# In commands/flow.py
import logging
from typing import Generator, Any
from .parser import Command
from core.expresion_evaluator import ExpressionEvaluator
from core.conversation import Conversation
from simpleeval import simple_eval, NameNotDefined, InvalidExpression
import random
from utils.llm import llm_client_response

log = logging.getLogger(__name__)

class CommandError(Exception):
    """Raised when a command fails execution."""
    pass

class ExecutionState:
    """Mutable container for the current execution flow."""
    def __init__(self, conversation, commands):
        self.stack = []
        self.conversation = conversation
        self.commands = commands

def cmd_solve(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Jumps into a sub-conversation or a strategy.
    Modifies the ExecutionState to push the current context onto the stack.
    """
    if not args:
        raise CommandError("Solve command requires a strategy or conversation name.")

    strategy_name = args[0]
    
    # Extract what we need from ctx
    state: 'ExecutionState' = ctx['state']  # Our mutable state object
    strategies = state.conversation.strategies
    conversations = state.conversation.conversations

    # 1. Validation
    if strategy_name not in strategies and strategy_name not in conversations:
        raise CommandError(f"Unknown strategy or conversation: {strategy_name}")

    # 2. Flow Control Mutation
    if strategy_name in conversations:
        # Push CURRENT state to stack before jumping
        state.stack.append((state.conversation, state.commands))
        
        # Prepare new conversation, copying current slots
        conv_args = conversations[strategy_name].copy()
        conv_args['slots'] = dict(evaluator.slots) # Get clean slots from evaluator
       
        log.info(f"Starting execution of conversation {strategy_name}")
        state.conversation = Conversation(**conv_args)
        state.commands = list(state.conversation.commands)
    else:
        # It's a strategy
        state.stack.append((state.commands,))
        state.commands = list(strategies[strategy_name])
        log.info(f"Starting execution of strategy {strategy_name}")
        
    # 3. Return status (yielded as the final value of the generator)
    yield from () # Yield once to maintain the Generator pattern, even if no output is sent to user
    return {'command': 'solve', 'ok': True}

def cmd_return(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Saves a variable from the current slots into the conversation's 'return' 
    dictionary so it can be passed back to the parent caller.
    """
    if not args:
        yield from ()# Maintain generator pattern
        return {'command': 'return', 'ok': False, 'error': 'Missing slot name'}

    slot_name = args[0]
    
    # 1. Check if the variable exists in the evaluator's slots
    if slot_name not in evaluator.slots:
        yield from ()
        # Note: In your original code, ok=False triggers the interpreter to stop.
        # If you prefer it to just silently fail without stopping, change ok to True.
        return {
            'command': 'return', 
            'value': slot_name, 
            'ok': False
        }
    
    # 2. Get the value
    value = evaluator.slots[slot_name]
    
    # 3. Mutate the conversation state via the ctx dictionary
    # state.conversation points to the active Conversation object
    ctx['state'].conversation.return_[slot_name] = value
    
    # 4. Yield to maintain generator protocol, then return the status
    yield from ()
    return {
        'command': 'return',
        'variable': slot_name,
        'value': value,
        'ok': True,
    }

def cmd_llm(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Resolves a prompt, sends it to the LLM client, and optionally saves the response to a slot.
    """
    if not args:
        yield from ()
        return {'command': 'llm', 'ok': False, 'error': 'Missing prompt key or text'}

    key = args[0]
    prompts = ctx.get('prompts', {})
    
    # 1. Resolve the prompt string
    if key in prompts:
        raw_prompt = prompts[key].strip()
        # Dynamically build an f-string and evaluate it safely using the evaluator
        fmt_str = f'f"""{raw_prompt}"""' if '\n' in raw_prompt else f'f"{raw_prompt}"'
        
        try:
            prompt = evaluator.eval_expression(fmt_str)
        except Exception as e:
            # If simpleeval fails, fall back to the raw text
            prompt = raw_prompt 
    else:
        # If it's not a defined prompt, treat the arg as a raw string and format it
        try:
            prompt = key.format_map(evaluator.slots)
        except KeyError:
            prompt = key  # Fallback if a slot is missing

    # 2. Call the LLM (Extract client from context)
    llm_client = ctx.get('llm_client')
    if not llm_client:
        yield from ()
        return {'command': 'llm', 'ok': False, 'error': 'LLM Client not found in context'}

    response = llm_client_response(llm_client, prompt)

    # 3. Handle state mutation based on arguments
    if len(args) == 1:
        # Just yield the response to the UI/stream
        yield {"cmd": "llm", "args": [response]}
        return {'command': 'llm', 'value': [response], 'ok': True}
        
    elif len(args) >= 2:
        variable = args[1]
        
        # CRITICAL: Use update_slots() so the evaluator rebuilds its internal 
        # simpleeval context. If you just do `evaluator.slots[var] = response`, 
        # the next simpleeval call won't know about this new variable!
        evaluator.update_slots({variable: response})
        
        yield {"cmd": "llm", "args": [response]}
        return {
            'command': 'llm',
            'variable': variable,
            'value': [response],
            'ok': True,
        }

def cmd_say(args, context:dict, evaluator: ExpressionEvaluator, callback) -> Generator[dict, Any, None]:
    texts=None
    if len(args)==0 and context['is_continuation']:
        texts=context['prev_status']['value']
    elif len(args)==1:
        key = args[0]
        if key in context['templates']:
            texts = resolve_template(key, context, evaluator)
        else:
            texts = [key.format_map(evaluator.slots)]
    yield {"cmd": "say", "args": texts}
    return {'command': 'say', 'value': texts, 'ok': True}

def cmd_listen(args, context:dict, evaluator: ExpressionEvaluator, callback) -> Generator[dict, Any, None]:
    variable = str(args[0])
    yield {"cmd": "listen"}
    user_input = callback()
    evaluator.slots[variable] = user_input or ""
    return {
        'command': 'listen',
        'value': user_input or "",
        'variable': variable,
        'ok': True,
    }

def cmd_set(args, context:dict, evaluator: ExpressionEvaluator, callback) -> Generator[dict, Any, None]:
    if not args:
        yield from ()
        return {'command': 'set', 'ok': False}

    variable = str(args[0])
    if  len(args) == 1 and context['is_continuation']:
        value = context['prev_status'].get('value')
    else:
        value = args[1:]

    evaluator.slots[variable] = value
    yield from ()
    return {'command': 'set', 'value': value, 'variable': variable, 'ok': True}


def cmd_exec(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Evaluates arguments safely, finds a restricted function, and executes it.
    """
    if not args:
        yield from ()
        return {'command': 'exec', 'ok': False, 'error': 'Missing function name'}

    func_name = args[0]
    
    # 1. Evaluate the arguments passed to the function
    # The evaluator automatically has access to both slots and _restricted_locals!
    try:
        evaluated_args = [evaluator.eval_expression(arg) for arg in args[1:]]
    except Exception as e:
        # Raising CommandError automatically tells the Interpreter to halt
        raise CommandError(f"Exec argument evaluation failed for '{func_name}': {e}")

    # 2. Handle 'continuation' (piping the previous command's output into this one)
    # The Interpreter will inject 'is_continuation' and 'prev_status' into ctx
    if ctx.get('is_continuation'):
        prev_value = ctx.get('prev_status', {}).get('value')
        evaluated_args.append(prev_value)
    
    # 3. Verify the function actually exists in our safe context
    if func_name not in evaluator.context:
        raise CommandError(f"Exec function '{func_name}' is not defined.")

    # 4. Execute the restricted function safely
    try:
        output = evaluator.context[func_name](*evaluated_args)
        
        yield from () # Maintain generator protocol
        return {
            'command': 'exec',
            'value': output,
            'ok': True
        }
    except Exception as e:
        raise CommandError(f"Exec function '{func_name}' crashed: {e}")

def cmd_remember(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Saves a variable to memory (slots) and persists it to the database via the MemoryStore.
    """
    is_continuation = ctx.get('is_continuation')
    prev_status = ctx.get('prev_status', {})

    # 1. Resolve variable and value based on arguments and continuation state
    if len(args) >= 2:
        variable, value = str(args[0]), args[1]
    elif len(args) == 1:
        variable = str(args[0])
        value = prev_status.get('value') if is_continuation else None
    else:
        variable = prev_status.get('variable')
        value = prev_status.get('value')

    # 2. Validation
    if not variable or value is None:
        yield from ()
        return {'command': 'remember', 'ok': False, 'error': 'Missing variable or value'}

    # 3. Update the Evaluator's state (which updates slots)
    evaluator.update_slots({variable: value})

    # 4. Persist to Database via injected MemoryStore
    store = ctx.get('memory_store')
    if not store:
        raise CommandError("MemoryStore is not configured in context.")

    # Grab user/project info from the active conversation state
    conversation = ctx['state'].conversation
    
    try:
        store.remember(
            user_id=conversation.user_id,
            project_path=str(conversation.project_pathname),
            variable=variable,
            value=value
        )
    except Exception as e:
        # Let the interpreter catch this and halt execution gracefully
        raise CommandError(f"Database remember failed for '{variable}': {e}")

    yield from ()
    return {
        'command': 'remember',
        'value': value,
        'variable': variable,
        'ok': True
    }

def cmd_info(
    args: list, 
    ctx: dict, 
    evaluator: 'ExpressionEvaluator', 
    callback: callable
) -> Generator[dict, Any, dict]:
    """
    Formats and yields requested diagnostic information (slots, name, status).
    """
    info_data = []
    
    # Iterate through requested info types, cleaning up strings (e.g. handling "slots,name")
    for raw_type in args:
        info_type = str(raw_type).replace(",", "")
        
        if info_type == "slots":
            # Get the current, up-to-date slots directly from the evaluator
            info_data.append(('slots', evaluator.slots))
            
        elif info_type == "name":
            # Fallback to 'unknown' if the interpreter forgot to pass the name in ctx
            state=ctx.get('state')
            info_data.append(('name', state.conversation.name))

        elif info_type == "strategies":
            # Fallback to 'unknown' if the interpreter forgot to pass the name in ctx
            state=ctx.get('state')
            info_data.append(('strategies', state.conversation.strategies.keys()))

        elif info_type == "status":
            # Grab the previous command's status from the context payload
            info_data.append(('status', ctx.get('prev_status', {})))

    # Yield the actual payload to the UI/callback stream FIRST
    yield {"cmd": "info", "args": info_data}
    
    # Return the internal status tracker SECOND
    return {
        'command': 'info',
        'value': info_data[-1] if info_data else [],
        'ok': bool(info_data)  # False if no valid args were passed
    }


def resolve_template(
        name: str,
        ctx: dict, 
        evaluator: 'ExpressionEvaluator'):
    t = ctx['templates'][name]
    
    try:
        if 'CASES' in t:
            val = simple_eval(t['SLOT'], names=evaluator.slots)
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
                
        return [simple_eval(s, names=evaluator.slots) for s in fmt_strings]
        
    except (NameNotDefined, InvalidExpression, KeyError) as e:
        log.error(f"Failed to resolve template {name}: {e}")
        return [f"[Error resolving template {name}]"]

