import ast
from typing import Any
from simpleeval import simple_eval, NameNotDefined, InvalidExpression

# Import your parser models
from .parser import Clause, Condition

class EvaluationError(Exception):
    """Custom exception raised when an expression or condition cannot be evaluated."""
    pass


class ExpressionEvaluator:
    """
    Handles all variable resolution, literal parsing, mathematical coercion,
    and safe execution of dynamic expressions (simpleeval).
    """

    def __init__(self, restricted_locals: dict, initial_slots: dict):
        # The combined dictionary passed to simpleeval. 
        # This solves the '_settings does not exist' bug permanently.
        self._restricted_locals = restricted_locals
        self.slots = initial_slots
        self._build_context()

    def _build_context(self):
        """Rebuilds the execution context whenever slots are updated."""
        self.context = {**self._restricted_locals, **self.slots}

    def update_slots(self, new_slots: dict):
        """Called by the Interpreter when a 'set' or 'listen' command updates state."""
        self.slots.update(new_slots)
        self._build_context()  # Ensure simpleeval sees the new variables

    def eval_expression(self, expr: str) -> Any:
        """
        Safely evaluates a string expression (e.g., "_settings.get('x') + 1").
        Used primarily in the 'exec' and template resolution commands.
        """
        try:
            return simple_eval(expr, names=self.context)
        except (NameNotDefined, InvalidExpression) as e:
            raise EvaluationError(f"Failed to evaluate expression '{expr}': {e}")

    def resolve_value(self, key: str) -> Any:
        """
        Looks up a key in the slots. 
        If not found, attempts to parse it as a Python literal (1, True, 'string').
        Falls back to returning the raw string.
        """
        if key in self.slots:
            return self.slots[key]
        
        try:
            return ast.literal_eval(key)
        except (ValueError, SyntaxError):
            # FIX: Original code returned False here, breaking string comparisons
            return key

    def evaluate_condition(self, condition: Condition) -> bool:
        """
        Evaluates a parsed Condition (one or more OR-joined Clauses).
        Returns True if ANY of the clauses evaluate to True.
        """
        for clause in condition.clauses:
            if self.evaluate_clause(clause):
                return True
        return False

    def evaluate_clause(self, clause: Clause) -> bool:
        """Evaluates a single clause (e.g., 'age > 18' or 'not active')."""
        left_val = self.resolve_value(clause.left)

        # If no operator, just check truthiness (e.g., "if logged_in")
        if clause.op is None:
            result = bool(left_val)
        else:
            if clause.right is None:
                raise EvaluationError(f"Operator '{clause.op}' requires a right operand.")
            
            right_val = self.resolve_value(clause.right)
            result = self._apply_op(left_val, clause.op, right_val)

        # Apply negation (e.g., "if not active")
        return (not result) if clause.negate else result

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

        if op not in ops:
            raise EvaluationError(f"Unsupported operator: {op}")

        try:
            return ops[op](left, right)
        except TypeError:
            # e.g., trying to compare a string to a dict
            return False

    def _coerce(self, left: Any, right: Any) -> tuple[Any, Any]:
        """Ensures numeric strings compare as numbers, not lexicographically."""
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
        
        # If BOTH can be converted to floats, compare as floats.
        # Otherwise, compare as their original types.
        if isinstance(l_num, float) and isinstance(r_num, float):
            return l_num, r_num
            
        return left, right
