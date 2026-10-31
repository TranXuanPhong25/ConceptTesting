"""
Symbolic Execution Module for Panta
Uses Z3 solver with SSA-style environment tracking to generate concrete input values.
"""

import re
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from ..helpers.panta_logger import pantaLogger


class SymbolicExecutor:
    """
    Symbolic executor that uses Z3 with SSA-style environment tracking.
    Parses assignments and maintains variable values throughout the path.
    """

    def __init__(self, language: str = "java", solving_timeout: int = 300,
                 enable_llm_path_solving: bool = False,
                 enable_llm_verify: bool = False,
                 llm_verify_max_rejections: int = 3,
                 llm_invoker=None):
        """
        Initialize the symbolic executor.

        Args:
            language: Programming language ("java" or "python")
            solving_timeout: Maximum total seconds allowed for one solving session
                             (across all paths). Defaults to 300 s.
            enable_llm_path_solving: When True, paths with non-numerical conditions
                                     (method calls, null checks, enum constants, etc.)
                                     are sent to an LLM instead of Z3.
            enable_llm_verify: When True, verify each LLM path-solving answer with
                               a second LLM pass before accepting it.
            llm_verify_max_rejections: Maximum number of verifier "No" responses
                                       before the path is skipped.
            llm_invoker: LLMInvocation instance to use for LLM path solving.
        """
        self.language = language
        self.solving_timeout = solving_timeout
        self.enable_llm_path_solving = enable_llm_path_solving
        self.enable_llm_verify = enable_llm_verify
        self.llm_verify_max_rejections = max(1, int(llm_verify_max_rejections))
        self.llm_invoker = llm_invoker
        self._session_start: Optional[float] = None
        self.logger = pantaLogger.initialize_logger(__name__)

        # Try to import Z3, but make it optional
        try:
            import z3
            self.z3 = z3
            self.z3_available = True
            self.logger.info("Z3 solver initialized successfully with SSA-style tracking")
        except ImportError:
            self.z3 = None
            self.z3_available = False
            self.logger.warning("Z3 not available. Symbolic execution will be disabled. "
                              "Install with: pip install z3-solver")

    # ------------------------------------------------------------------
    # Session-level timeout helpers
    # ------------------------------------------------------------------

    def start_solve_session(self) -> None:
        """
        Mark the beginning of a new solving session.

        Call this once before iterating over a set of paths so that the
        total Z3 solving time across all paths is bounded by ``solving_timeout``.
        """
        self._session_start = time.time()
        self.logger.debug(f"Symbolic execution session started (timeout={self.solving_timeout}s)")

    def is_session_timed_out(self) -> bool:
        """Return True if the current session has exceeded ``solving_timeout``."""
        if self._session_start is None:
            return False
        return (time.time() - self._session_start) >= self.solving_timeout

    def _remaining_session_ms(self) -> Optional[int]:
        """
        Return the milliseconds remaining in the current session, or None if
        no session has been started.  Clipped to at least 1 ms so that Z3
        doesn't receive 0 (which would mean *no* timeout in some versions).
        """
        if self._session_start is None:
            return None
        elapsed = time.time() - self._session_start
        remaining = self.solving_timeout - elapsed
        return max(1, int(remaining * 1000))

    # ------------------------------------------------------------------

    def solve_path_constraints(self, path_nodes: List[Tuple], method_params: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Solve constraints for a given path using SSA-style environment tracking.

        Args:
            path_nodes: List of (line_numbers, statement, conditional) tuples
            method_params: List of method parameters with their types

        Returns:
            Dictionary mapping variable names to concrete values, or None if unsolvable
        """
        if not self.z3_available:
            return None

        # Abort immediately if the session budget is already exhausted
        if self.is_session_timed_out():
            self.logger.debug("Symbolic execution session timed out; skipping path.")
            return None

        try:
            solver = self.z3.Solver()

            # Apply remaining session budget as Z3's per-check timeout
            remaining_ms = self._remaining_session_ms()
            if remaining_ms is not None:
                solver.set("timeout", remaining_ms)

            env = {}  # Maps variable name to current Z3 expression
            input_symbols = {}  # Preserves the original symbolic input variables
            var_types = {param.get('name', ''): param.get('type', '')
                         for param in (method_params or []) if param.get('name')}
            placeholder_counter = [0]  # Use list to allow modification in nested function

            # Identify input variables from the path
            input_vars = self._identify_input_variables(path_nodes, method_params)
            self.logger.debug(f"Input variables: {input_vars}")

            # Initialize Z3 variables for all input variables
            for var_name in input_vars:
                symbol = self._make_symbol(var_name, var_types.get(var_name))
                env[var_name] = symbol
                input_symbols[var_name] = symbol

            # Process each node in the path
            for node in path_nodes:
                statement = node[1]
                conditional = node[2]

                # Skip loop constructs
                if self._is_loop_statement(statement):
                    self.logger.debug(f"Skipping loop: {statement}")
                    continue

                if conditional is not None:
                    # This is a conditional statement (if, while, etc.)
                    constraint = self._parse_conditional_statement(
                        statement, env, conditional, placeholder_counter, var_types
                    )
                    if constraint is not None:
                        solver.add(constraint)
                        self.logger.debug(f"Added constraint from: {statement}")
                else:
                    # This is an assignment or other statement
                    self._process_assignment(statement, env, var_types)

            # Solve the constraints
            solution = {}
            check_result = solver.check()
            if check_result == self.z3.unknown:
                self.logger.debug("Z3 solver timed out (returned unknown) for this path.")
                return None
            if check_result == self.z3.sat:
                model = solver.model()

                for var_name in input_vars:
                    z3_var = input_symbols.get(var_name)
                    if z3_var is not None:
                        val = model.eval(z3_var, model_completion=True)
                        if val is not None:
                            extracted = self._extract_model_value(val)
                            if extracted is not None:
                                solution[var_name] = extracted
                            else:
                                self.logger.debug(f"Could not extract value for {var_name}")

                self.logger.debug(f"Solved constraints with solution: {solution}")
                return solution if solution else None
            else:
                self.logger.debug("Path constraints are unsatisfiable")
                return None

        except Exception as e:
            self.logger.warning(f"Error during symbolic execution: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

    def _identify_input_variables(self, path_nodes: List[Tuple], method_params: List[Dict] = None) -> set:
        """
        Identify which variables are input parameters vs local variables.

        Args:
            path_nodes: Path nodes
            method_params: Method parameters

        Returns:
            Set of input variable names
        """
        # If method_params provided, use those
        if method_params:
            return {param.get('name', '') for param in method_params if param.get('name')}

        # Otherwise, identify from path: variables used before assignment
        assigned_vars = set()
        used_vars = set()
        loop_vars = set()

        for node in path_nodes:
            statement = node[1]
            conditional = node[2]

            # Extract loop variables from for/foreach loops
            if self._is_loop_statement(statement):
                loop_var = self._extract_loop_variable(statement)
                if loop_var:
                    loop_vars.add(loop_var)

            # Check if this is an assignment
            lhs, rhs = self._parse_assignment_parts(statement)
            if lhs and rhs:
                # Extract variables used ONLY in the right-hand side
                vars_in_rhs = self._extract_variables_from_expr(rhs)
                used_vars.update(vars_in_rhs)
                # Only mark as assigned if it's a NEW variable (not previously used)
                # This distinguishes:
                #   int rem = n % 3  (new local variable)
                #   n = n | 1        (parameter reassignment)
                # Parameters can be reassigned but remain input parameters
                if lhs not in used_vars:
                    assigned_vars.add(lhs)
                continue

            # Extract variables used in conditions
            if conditional is not None:
                vars_in_condition = self._extract_variables_from_expr(statement)
                used_vars.update(vars_in_condition)

        # Input variables are those used before being assigned, excluding loop variables
        input_vars = used_vars - assigned_vars - loop_vars

        # Filter out common keywords, method names, and class names
        input_vars = {v for v in input_vars if not self._is_keyword_or_method(v, path_nodes)}

        return input_vars

    def _is_keyword_or_method(self, var_name: str, path_nodes: List[Tuple]) -> bool:
        """Check if a variable name is actually a keyword or method name."""
        keywords = {'true', 'false', 'null', 'this', 'super', 'return', 'new',
                   'int', 'long', 'float', 'double', 'boolean', 'char', 'void'}
        if var_name.lower() in keywords:
            return True

        # Check if it appears with parentheses (method call)
        for node in path_nodes:
            statement = node[1]
            if re.search(rf'\b{re.escape(var_name)}\s*\(', statement):
                return True

        return False

    def _is_loop_statement(self, statement: str) -> bool:
        """Check if statement is a loop construct."""
        statement = statement.strip()
        return (statement.startswith('while') or
                statement.startswith('for') or
                re.match(r'^\s*(while|for)\s*\(', statement) is not None)

    def _parse_conditional_statement(self, statement: str, env: Dict, conditional: bool,
                                     placeholder_counter: List[int], var_types: Dict[str, str]) -> Optional[Any]:
        """
        Parse a conditional statement and return Z3 constraint.

        Args:
            statement: The statement string
            env: Current environment mapping variables to Z3 expressions
            conditional: True if condition was taken, False if not taken
            placeholder_counter: Counter for generating unique placeholder names

        Returns:
            Z3 constraint or None
        """
        # Extract the condition
        condition = self._extract_condition(statement)
        if not condition:
            return None

        # Check if condition contains method call
        if self._contains_method_call(condition):
            # Use boolean placeholder
            placeholder = self.z3.Bool(f"method_call_{placeholder_counter[0]}")
            placeholder_counter[0] += 1
            self.logger.debug(f"Created placeholder for method call: {condition}")
            return placeholder if conditional else self.z3.Not(placeholder)

        # Parse the condition into Z3 expression
        condition_expr = self._parse_condition_expr(condition, env, var_types)
        if condition_expr is None:
            return None

        # Apply the boolean value (conditional)
        if conditional:
            # Condition is True, use as-is
            return condition_expr
        else:
            # Condition is False, negate it
            return self.z3.Not(condition_expr)

    def _extract_condition(self, statement: str) -> Optional[str]:
        """Extract condition from if/while statement."""
        # Java/C-style: if (condition) or while (condition)
        # Need to handle nested parentheses properly
        match = re.search(r'(?:if|while)\s*\(', statement, re.IGNORECASE)
        if match:
            start_pos = match.end() - 1  # Position of opening '('
            # Find matching closing parenthesis
            paren_count = 0
            for i in range(start_pos, len(statement)):
                if statement[i] == '(':
                    paren_count += 1
                elif statement[i] == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        # Found matching closing paren
                        condition = statement[start_pos + 1:i].strip()
                        self.logger.debug(f"Extracted condition from '{statement}' -> '{condition}'")
                        # Validate and fix any unbalanced parentheses
                        condition = self._fix_unbalanced_parentheses(condition)
                        return condition

            # If no matching paren found, statement might be incomplete
            # Extract what we can from start_pos+1 to end
            self.logger.warning(f"No matching parenthesis found in statement: {statement}")
            condition = statement[start_pos + 1:].strip()
            # Remove trailing ) if present
            if condition.endswith(')'):
                condition = condition[:-1].strip()
            self.logger.debug(f"Extracted partial condition: '{condition}'")
            # Validate and fix any unbalanced parentheses
            condition = self._fix_unbalanced_parentheses(condition)
            return condition if condition else None

        # Python-style: if condition: or while condition:
        match = re.search(r'(?:if|while)\s+(.*?)(?:\s*:|\s+is\s+)', statement, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    def _fix_unbalanced_parentheses(self, condition: str) -> str:
        """Fix unbalanced parentheses in a condition string."""
        if not condition:
            return condition

        # Count parentheses
        open_count = condition.count('(')
        close_count = condition.count(')')

        if open_count == close_count:
            return condition

        # More closing parens - remove trailing ones
        if close_count > open_count:
            diff = close_count - open_count
            # Remove trailing ) characters
            while diff > 0 and condition.endswith(')'):
                condition = condition[:-1].strip()
                diff -= 1
        # More opening parens - add closing ones
        elif open_count > close_count:
            diff = open_count - close_count
            condition = condition + ')' * diff

        self.logger.debug(f"Fixed unbalanced parentheses: now '{condition}'")
        return condition

    def _contains_method_call(self, condition: str) -> bool:
        """Check if condition contains a method call or instanceof check."""
        # instanceof has no parseable comparison operator — treat like a method call
        if re.search(r'\binstanceof\b', condition):
            return True
        # Look for pattern: word followed by (
        tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', condition)
        for token in tokens:
            if token.lower() not in ['if', 'while', 'for', 'switch']:
                return True
        return False

    def _should_strip_outer_parens(self, condition: str) -> bool:
        """
        Check if outer parentheses actually wrap the entire condition.

        For example:
        - "((k < 0))" -> True (outer parens wrap everything)
        - "(k < 0) || (k >= 5)" -> False (outer parens are part of sub-expressions)
        """
        if not (condition.startswith('(') and condition.endswith(')')):
            return False

        # Count parentheses from start to see if opening ( matches ending )
        paren_count = 0
        for i, char in enumerate(condition):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                # If count goes to 0 before the end, outer parens don't wrap everything
                if paren_count == 0 and i < len(condition) - 1:
                    return False

        return True

    def _parse_condition_expr(self, condition: str, env: Dict, var_types: Dict[str, str]) -> Optional[Any]:
        """
        Parse a condition expression into Z3 constraint.

        Supports:
        - Logical operators: ||, &&
        - Comparisons: ==, !=, <, >, <=, >=
        - Null checks: x == null, x != null

        Args:
            condition: Condition string (e.g., "n < 0", "a > 0 || b < 1")
            env: Current environment

        Returns:
            Z3 expression or None
        """
        condition = condition.strip()
        self.logger.debug(f"_parse_condition_expr: input='{condition}'")

        # Fix any unbalanced parentheses before parsing
        condition = self._fix_unbalanced_parentheses(condition)
        self.logger.debug(f"_parse_condition_expr: after fix_unbalanced='{condition}'")

        # Strip outer parentheses ONLY if they wrap the entire expression
        if self._should_strip_outer_parens(condition):
            condition = condition[1:-1].strip()
            self.logger.debug(f"_parse_condition_expr: after strip_outer_parens='{condition}'")

        if condition.startswith('!'):
            negated = self._parse_condition_expr(condition[1:].strip(), env, var_types)
            if negated is not None:
                return self.z3.Not(negated)
            self.logger.debug(f"_parse_condition_expr: failed to parse negated condition '{condition}'")
            return None

        # Handle logical OR (||) - lowest precedence
        parts = self._split_by_operator(condition, '||')
        if len(parts) > 1:
            self.logger.debug(f"_parse_condition_expr: split by || -> {parts}")
            sub_exprs = []
            for part in parts:
                sub_expr = self._parse_condition_expr(part.strip(), env, var_types)
                if sub_expr is None:
                    self.logger.debug(f"_parse_condition_expr: failed to parse OR part '{part}'")
                    return None
                sub_exprs.append(sub_expr)
            result = self.z3.Or(*sub_exprs)
            self.logger.debug(f"_parse_condition_expr: OR result={result}")
            return result

        # Handle logical AND (&&) - higher precedence than ||
        parts = self._split_by_operator(condition, '&&')
        if len(parts) > 1:
            self.logger.debug(f"_parse_condition_expr: split by && -> {parts}")
            sub_exprs = []
            for part in parts:
                sub_expr = self._parse_condition_expr(part.strip(), env, var_types)
                if sub_expr is None:
                    self.logger.debug(f"_parse_condition_expr: failed to parse AND part '{part}'")
                    return None
                sub_exprs.append(sub_expr)
            result = self.z3.And(*sub_exprs)
            self.logger.debug(f"_parse_condition_expr: AND result={result}")
            return result

        # Handle null comparisons specially
        # Pattern: var == null or this.field != null or object.field == null
        # Support dotted expressions like this.field, object.field.subfield
        null_match = re.match(r'([\w.]+)\s*(==|!=)\s*null', condition, re.IGNORECASE)
        if null_match:
            var_expr = null_match.group(1)
            op = null_match.group(2)

            # For dotted expressions like this.lexer, use the full expression as var name
            # Replace dots with underscores for Z3 variable name
            var_name = var_expr.replace('.', '_')

            # Ensure variable exists in env as BitVec
            if var_name not in env:
                env[var_name] = self.z3.BitVec(var_name + "_ref", 32)

            # null represented as 0 for reference types
            if op == '==':
                return env[var_name] == 0
            else:  # op == '!='
                return env[var_name] != 0

        # Reverse: null == var or null != this.field
        null_match = re.match(r'null\s*(==|!=)\s*([\w.]+)', condition, re.IGNORECASE)
        if null_match:
            op = null_match.group(1)
            var_expr = null_match.group(2)

            # Replace dots with underscores for Z3 variable name
            var_name = var_expr.replace('.', '_')

            if var_name not in env:
                env[var_name] = self.z3.BitVec(var_name + "_ref", 32)

            if op == '==':
                return env[var_name] == 0
            else:
                return env[var_name] != 0

        # Handle comparison operators
        # Check in order of longest first to avoid false matches (e.g., >= before >)
        for op in ['==', '!=', '<=', '>=', '<', '>']:
            if op in condition:
                # Split by operator while respecting parentheses
                if op == '<':
                    parts = self._split_by_operator(condition, op, not_followed_by='<', not_preceded_by='<')
                elif op == '>':
                    parts = self._split_by_operator(condition, op, not_followed_by='>', not_preceded_by='>')
                else:
                    parts = self._split_by_operator(condition, op)
                self.logger.debug(f"_parse_condition_expr: trying op '{op}', split -> {parts}")
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip(), env, var_types)
                    right = self._parse_expression(parts[1].strip(), env, var_types)
                    self.logger.debug(f"_parse_condition_expr: parsed left='{left}', right='{right}'")

                    if left is not None and right is not None:
                        left, right = self._coerce_numeric_pair(left, right)
                    if left is not None and right is not None:
                        if op == '==':
                            result = left == right
                        elif op == '!=':
                            result = left != right
                        elif op == '<':
                            result = left < right
                        elif op == '>':
                            result = left > right
                        elif op == '<=':
                            result = left <= right
                        elif op == '>=':
                            result = left >= right
                        self.logger.debug(f"_parse_condition_expr: comparison result={result}")
                        return result
                # If split succeeded, don't try other operators
                if len(parts) > 1:
                    break

        self.logger.debug(f"Could not parse condition: {condition}")
        return None

    def _process_assignment(self, statement: str, env: Dict, var_types: Dict[str, str]):
        """
        Process an assignment statement and update environment.

        Args:
            statement: Statement string (e.g., "n = n | 1", "int rem = n % 3")
            env: Environment to update
        """
        # Try to parse assignment: var = expr or type var = expr
        # Handles primitives (int, long) and class types (DSTZone, ArrayList<T>)
        declared_type = None
        assignment_match = re.match(
            r'(?:final\s+)?(?:(?P<type>[A-Za-z_][\w$]*(?:<[^<>]*>)?(?:\[\])?)\s+)?(?P<var>\w+)\s*=\s*(?P<expr>.+?)(?:\s*;)?$',
            statement, re.IGNORECASE)

        if not assignment_match:
            # Try simpler pattern: var = expr or var += expr, var -= expr, etc.
            assignment_match = re.match(r'(\w+)\s*(<<=|>>=|>>>=|[+\-*/%|&^]?=)\s*(.+?)(?:\s*;)?$', statement)
            if assignment_match:
                var_name = assignment_match.group(1)
                op = assignment_match.group(2)
                expr_str = assignment_match.group(3)

                # Handle compound assignments (+=, -=, etc.)
                if op == '+=':
                    expr_str = f"{var_name} + ({expr_str})"
                elif op == '-=':
                    expr_str = f"{var_name} - ({expr_str})"
                elif op == '*=':
                    expr_str = f"{var_name} * ({expr_str})"
                elif op == '/=':
                    expr_str = f"{var_name} / ({expr_str})"
                elif op == '%=':
                    expr_str = f"{var_name} % ({expr_str})"
                elif op == '|=':
                    expr_str = f"{var_name} | ({expr_str})"
                elif op == '&=':
                    expr_str = f"{var_name} & ({expr_str})"
                elif op == '^=':
                    expr_str = f"{var_name} ^ ({expr_str})"
                elif op == '<<=':
                    expr_str = f"{var_name} << ({expr_str})"
                elif op == '>>=':
                    expr_str = f"{var_name} >> ({expr_str})"
                elif op == '>>>=':
                    expr_str = f"{var_name} >>> ({expr_str})"
                # else op == '=', use expr_str as-is
            else:
                return  # Not an assignment
        else:
            declared_type = assignment_match.group('type')
            var_name = assignment_match.group('var')
            expr_str = assignment_match.group('expr')
            if declared_type:
                var_types[var_name] = declared_type

        # Skip if expression contains method calls or object creation
        if self._contains_method_call(expr_str) or 'new ' in expr_str.lower():
            self.logger.debug(f"Skipping assignment with method call/new: {statement}")
            if var_name not in env:
                env[var_name] = self._make_symbol(var_name, var_types.get(var_name, declared_type))
            return

        # Check if RHS is a boolean expression (contains comparison operators)
        # This handles cases like: isCounterClockWise = n > 0
        has_comparison = self._has_top_level_boolean_expression(expr_str)

        if has_comparison:
            # Parse as a condition expression (returns Z3 Bool)
            expr = self._parse_condition_expr(expr_str, env, var_types)
            if expr is not None:
                # Store the boolean result
                env[var_name] = expr
                self.logger.debug(f"Boolean assignment: {var_name} = {expr_str}")
        else:
            # Parse as arithmetic expression
            expr = self._parse_expression(expr_str, env, var_types)
            if expr is not None:
                env[var_name] = expr
                self.logger.debug(f"Assignment: {var_name} = {expr_str}")

    def _has_top_level_boolean_expression(self, expr_str: str) -> bool:
        """
        Return True when the expression should be parsed as a boolean condition.

        This intentionally ignores bit-shift operators like ``<<`` / ``>>`` / ``>>>``,
        which contain ``<`` / ``>`` characters but are arithmetic/bitwise expressions.
        """
        if len(self._split_by_operator(expr_str, '||')) > 1:
            return True
        if len(self._split_by_operator(expr_str, '&&')) > 1:
            return True

        for op in ['==', '!=', '<=', '>=']:
            if len(self._split_by_operator(expr_str, op)) > 1:
                return True

        # Top-level < or > should count as comparisons only when they are not part of
        # a shift operator.
        if len(self._split_by_operator(expr_str, '<', not_followed_by='<', not_preceded_by='<')) > 1:
            return True
        if len(self._split_by_operator(expr_str, '>', not_followed_by='>', not_preceded_by='>')) > 1:
            return True

        return False

    def _normalize_type_name(self, type_name: Optional[str]) -> str:
        """Normalize a Java type string for lightweight symbolic typing."""
        if not type_name:
            return ""
        normalized = re.sub(r'\bfinal\b', '', type_name).strip()
        normalized = re.sub(r'<.*?>', '', normalized)
        normalized = normalized.replace("...", "[]")
        normalized = re.sub(r'\s+', '', normalized)
        return normalized

    def _type_spec(self, type_name: Optional[str]) -> Tuple[str, Optional[int]]:
        """Map a Java type name to a symbolic sort category."""
        normalized = self._normalize_type_name(type_name)
        if normalized in {'byte', 'short', 'int', 'long', 'char'}:
            widths = {'byte': 8, 'short': 16, 'int': 32, 'long': 64, 'char': 16}
            return "bitvec", widths[normalized]
        if normalized in {'float', 'double'}:
            return "real", None
        if normalized in {'boolean', 'bool'}:
            return "bool", None
        return "bitvec", 32

    def _make_symbol(self, var_name: str, type_name: Optional[str] = None):
        """Create a typed symbolic variable for the given name."""
        kind, width = self._type_spec(type_name)
        if kind == "real":
            return self.z3.Real(var_name)
        if kind == "bool":
            return self.z3.Bool(var_name)
        return self.z3.BitVec(var_name, width or 32)

    def _is_bool_expr(self, expr: Any) -> bool:
        return self.z3.is_bool(expr) if expr is not None else False

    def _is_real_expr(self, expr: Any) -> bool:
        return expr is not None and self.z3.is_real(expr)

    def _is_bitvec_expr(self, expr: Any) -> bool:
        return expr is not None and self.z3.is_bv(expr)

    def _coerce_bitvec(self, expr: Any, width: int, signed: bool = True) -> Optional[Any]:
        if expr is None or not self._is_bitvec_expr(expr):
            return None
        current_width = expr.size()
        if current_width == width:
            return expr
        if current_width > width:
            return self.z3.Extract(width - 1, 0, expr)
        ext = width - current_width
        if signed:
            return self.z3.SignExt(ext, expr)
        return self.z3.ZeroExt(ext, expr)

    def _bitvec_to_real(self, expr: Any) -> Any:
        return self.z3.ToReal(self.z3.BV2Int(expr, is_signed=True))

    def _coerce_numeric_pair(self, left: Any, right: Any) -> Tuple[Optional[Any], Optional[Any]]:
        """Coerce a numeric pair to compatible Z3 sorts for arithmetic/comparison."""
        if left is None or right is None:
            return None, None

        if self._is_real_expr(left) or self._is_real_expr(right):
            if self._is_bitvec_expr(left):
                left = self._bitvec_to_real(left)
            if self._is_bitvec_expr(right):
                right = self._bitvec_to_real(right)
            if self._is_real_expr(left) and self._is_real_expr(right):
                return left, right
            return None, None

        if self._is_bitvec_expr(left) and self._is_bitvec_expr(right):
            width = max(left.size(), right.size())
            return self._coerce_bitvec(left, width), self._coerce_bitvec(right, width)

        return None, None

    def _coerce_shift_operands(self, left: Any, right: Any) -> Tuple[Optional[Any], Optional[Any]]:
        if not self._is_bitvec_expr(left) or right is None:
            return None, None
        if self._is_real_expr(right):
            return None, None
        if not self._is_bitvec_expr(right):
            return None, None
        width = left.size()
        return left, self._coerce_bitvec(right, width, signed=False)

    def _extract_model_value(self, value: Any) -> Optional[Any]:
        """Convert a Z3 model value into a Python-friendly concrete value."""
        try:
            if self._is_bool_expr(value):
                return self.z3.is_true(value)
            if self._is_bitvec_expr(value):
                if hasattr(value, 'as_signed_long'):
                    return value.as_signed_long()
                return value.as_long()
            if self._is_real_expr(value):
                simplified = self.z3.simplify(value)
                if hasattr(simplified, 'numerator_as_long') and hasattr(simplified, 'denominator_as_long'):
                    numerator = simplified.numerator_as_long()
                    denominator = simplified.denominator_as_long()
                    if denominator == 1:
                        return numerator
                    return numerator / denominator
                return str(simplified)
        except Exception:
            pass

        try:
            simplified = self.z3.simplify(value)
            if self._is_bitvec_expr(simplified):
                if hasattr(simplified, 'as_signed_long'):
                    return simplified.as_signed_long()
                return simplified.as_long()
        except Exception:
            return None

        return None

    def _parse_numeric_literal(self, expr_str: str) -> Optional[Any]:
        """Parse Java/Python-style integer and floating-point literals into Z3 values."""
        literal = expr_str.strip()
        if not literal:
            return None

        # Normalize Java digit separators.
        literal = literal.replace('_', '')

        # Java decimal floating-point literals, optionally suffixed with f/F/d/D.
        if re.search(r'[fFdD]$', literal) or re.search(r'[.eE]', literal):
            normalized = re.sub(r'[fFdD]$', '', literal)
            try:
                return self.z3.RealVal(str(float(normalized)))
            except ValueError:
                return None

        # Java integral literal suffixes: L/l (long)
        width = 64 if re.search(r'[Ll]$', literal) else 32
        literal = re.sub(r'[Ll]$', '', literal)

        base = 10
        digits = literal
        if re.match(r'^0[xX][0-9a-fA-F]+$', literal):
            base = 16
            digits = literal[2:]
        elif re.match(r'^0[bB][01]+$', literal):
            base = 2
            digits = literal[2:]
        elif re.match(r'^0[0-7]+$', literal):
            # Java treats a leading-zero integral literal as octal.
            base = 8
            digits = literal[1:]
        elif not re.match(r'^[0-9]+$', literal):
            return None

        try:
            return self.z3.BitVecVal(int(digits, base), width)
        except ValueError:
            return None

    def _parse_assignment_lhs(self, statement: str) -> Optional[str]:
        """Extract the variable name being assigned (left-hand side)."""
        assignment_match = re.match(r'(?:final\s+)?(?:int|long|float|double|boolean|char)?\s*(\w+)\s*(?:<<=|>>=|>>>=|[+\-*/%|&^]?=)',
                                    statement, re.IGNORECASE)
        if assignment_match:
            return assignment_match.group(1)
        return None

    def _parse_assignment_parts(self, statement: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse assignment into LHS and RHS parts.

        Returns:
            Tuple of (lhs_variable, rhs_expression) or (None, None)
        """
        # Try: [final] [TypeName[<Generic>][[]]] var = expr
        # Handles both primitive types (int, long) and class types (DSTZone, ArrayList<T>)
        assignment_match = re.match(
            r'(?:final\s+)?(?:[A-Za-z_][\w$]*(?:<[^<>]*>)?(?:\[\])?\s+)?(\w+)\s*=\s*(.+?)(?:\s*;)?$',
            statement, re.IGNORECASE)
        if assignment_match:
            return assignment_match.group(1), assignment_match.group(2)

        # Try: var op= expr (compound assignments)
        assignment_match = re.match(r'(\w+)\s*(<<=|>>=|>>>=|[+\-*/%|&^]?=)\s*(.+?)(?:\s*;)?$', statement)
        if assignment_match:
            var_name = assignment_match.group(1)
            op = assignment_match.group(2)
            expr_str = assignment_match.group(3)

            # For compound assignments, the RHS includes the LHS variable
            # e.g., n += 2 means n = n + 2, so RHS is "n + 2"
            if op != '=':
                # The RHS in the code only has the increment part
                # We return just that part since we only care about what variables are USED
                # The LHS variable is already known
                return var_name, expr_str
            else:
                return var_name, expr_str

        return None, None

    def _extract_loop_variable(self, statement: str) -> Optional[str]:
        """
        Extract loop variable from for/foreach loop.

        Examples:
            for (int i = 0; i < n; i++) -> returns 'i'
            for (int p : SmallPrimes.PRIMES) -> returns 'p'
        """
        # For-each loop: for (type var : collection)
        match = re.match(r'for\s*\(\s*(?:final\s+)?(?:int|long|float|double|boolean|char|[A-Z]\w*)\s+(\w+)\s*:',
                        statement, re.IGNORECASE)
        if match:
            return match.group(1)

        # Traditional for loop: for (type var = ...; ...; ...)
        match = re.match(r'for\s*\(\s*(?:final\s+)?(?:int|long|float|double|boolean|char)\s+(\w+)\s*=',
                        statement, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _parse_expression(self, expr_str: str, env: Dict, var_types: Dict[str, str]) -> Optional[Any]:
        """
        Parse an expression into Z3 expression using current environment.

        Args:
            expr_str: Expression string
            env: Current environment

        Returns:
            Z3 expression or None
        """
        expr_str = expr_str.strip()

        # Strip outer parentheses if present
        if expr_str.startswith('(') and expr_str.endswith(')'):
            # Check if these are matching outer parentheses
            paren_count = 0
            for i, ch in enumerate(expr_str):
                if ch == '(':
                    paren_count += 1
                elif ch == ')':
                    paren_count -= 1
                    if paren_count == 0 and i == len(expr_str) - 1:
                        # Matching outer parentheses
                        expr_str = expr_str[1:-1].strip()
                        break

        # Handle literals
        if expr_str.lower() in ['null', 'none']:
            return self.z3.BitVecVal(0, 32)

        if expr_str.lower() == 'true':
            return self.z3.BitVecVal(1, 32)
        if expr_str.lower() == 'false':
            return self.z3.BitVecVal(0, 32)

        numeric_literal = self._parse_numeric_literal(expr_str)
        if numeric_literal is not None:
            return numeric_literal

        # Check for static field access (e.g., FastMath.PI, Math.PI)
        # Pattern: ClassName.FIELD_NAME
        if re.match(r'^[A-Z][a-zA-Z0-9_]*\.[A-Z_][A-Z0-9_]*$', expr_str):
            self.logger.debug(f"Skipping static field access: {expr_str}")
            return None

        # Check if it's a variable in environment
        if expr_str in env:
            return env[expr_str]

        # Numeric casts, e.g. (byte) value, (long) (x + 1)
        if expr_str.startswith('('):
            paren_count = 0
            for i, ch in enumerate(expr_str):
                if ch == '(':
                    paren_count += 1
                elif ch == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        cast_type = expr_str[1:i].strip()
                        rest = expr_str[i + 1:].strip()
                        if rest and re.match(r'^[A-Za-z_][A-Za-z0-9_<>\[\]]*$', cast_type):
                            operand = self._parse_expression(rest, env, var_types)
                            if operand is None:
                                break
                            kind, width = self._type_spec(cast_type)
                            if kind == "bitvec":
                                if self._is_bitvec_expr(operand):
                                    return self._coerce_bitvec(operand, width or 32)
                                if self._is_real_expr(operand):
                                    return self.z3.Int2BV(self.z3.ToInt(operand), width or 32)
                            elif kind == "real":
                                if self._is_real_expr(operand):
                                    return operand
                                if self._is_bitvec_expr(operand):
                                    return self._bitvec_to_real(operand)
                            break

        # Unary bitwise NOT
        if expr_str.startswith('~'):
            operand = self._parse_expression(expr_str[1:].strip(), env, var_types)
            if operand is not None:
                return ~operand

        # Unary plus/minus
        if expr_str.startswith('+'):
            return self._parse_expression(expr_str[1:].strip(), env, var_types)
        if expr_str.startswith('-'):
            operand = self._parse_expression(expr_str[1:].strip(), env, var_types)
            if operand is not None:
                return -operand

        # Handle binary operations with proper precedence (lowest to highest).
        # All splits are paren-aware via _split_by_operator.
        # For left-associativity: join all-but-last parts with the operator as the
        # left operand and take the last part as the right operand.

        # Bitwise OR (lowest precedence in this list)
        parts = self._split_by_operator(expr_str, '|')
        if len(parts) > 1:
            left = self._parse_expression('|'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_numeric_pair(left, right)
                if self._is_bitvec_expr(left) and self._is_bitvec_expr(right):
                    return left | right

        # Bitwise XOR
        parts = self._split_by_operator(expr_str, '^')
        if len(parts) > 1:
            left = self._parse_expression('^'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_numeric_pair(left, right)
                if self._is_bitvec_expr(left) and self._is_bitvec_expr(right):
                    return left ^ right

        # Bitwise AND
        parts = self._split_by_operator(expr_str, '&')
        if len(parts) > 1:
            left = self._parse_expression('&'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_numeric_pair(left, right)
                if self._is_bitvec_expr(left) and self._is_bitvec_expr(right):
                    return left & right

        # Unsigned right shift (Java >>>, must be checked before >>)
        parts = self._split_by_operator(expr_str, '>>>')
        if len(parts) > 1:
            left = self._parse_expression('>>>'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_shift_operands(left, right)
                if left is not None and right is not None:
                    return self.z3.LShR(left, right)

        # Signed arithmetic right shift (Java >>, but not >>>)
        parts = self._split_by_operator(expr_str, '>>', not_followed_by='>')
        if len(parts) > 1:
            left = self._parse_expression('>>'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_shift_operands(left, right)
                if left is not None and right is not None:
                    return left >> right  # Z3 BitVec >> is arithmetic right shift

        # Left shift (Java <<)
        parts = self._split_by_operator(expr_str, '<<')
        if len(parts) > 1:
            left = self._parse_expression('<<'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_shift_operands(left, right)
                if left is not None and right is not None:
                    return left << right

        # Addition and subtraction (same precedence, left-to-right)
        for op in ['+', '-']:
            parts = self._split_by_operator(expr_str, op)
            if len(parts) > 1:
                left = self._parse_expression(op.join(parts[:-1]).strip(), env, var_types)
                right = self._parse_expression(parts[-1].strip(), env, var_types)
                if left is not None and right is not None:
                    left, right = self._coerce_numeric_pair(left, right)
                if left is not None and right is not None:
                    if op == '+':
                        return left + right
                    else:
                        return left - right

        # Multiplication and division (higher precedence)
        for op in ['*', '/']:
            parts = self._split_by_operator(expr_str, op)
            if len(parts) > 1:
                left = self._parse_expression(op.join(parts[:-1]).strip(), env, var_types)
                right = self._parse_expression(parts[-1].strip(), env, var_types)
                if left is not None and right is not None:
                    left, right = self._coerce_numeric_pair(left, right)
                if left is not None and right is not None:
                    if op == '*':
                        return left * right
                    else:
                        return left / right

        # Modulo (same precedence as multiplication/division)
        parts = self._split_by_operator(expr_str, '%')
        if len(parts) > 1:
            left = self._parse_expression('%'.join(parts[:-1]).strip(), env, var_types)
            right = self._parse_expression(parts[-1].strip(), env, var_types)
            if left is not None and right is not None:
                left, right = self._coerce_numeric_pair(left, right)
            if left is not None and right is not None and self._is_bitvec_expr(left) and self._is_bitvec_expr(right):
                # Use signed remainder for Java compatibility
                return left % right

        # If not in environment and not parseable, create new BitVec variable
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', expr_str):
            if expr_str not in env:
                env[expr_str] = self._make_symbol(expr_str, var_types.get(expr_str))
            return env[expr_str]

        self.logger.debug(f"Could not parse expression: {expr_str}")
        return None

    def _in_parentheses(self, expr: str, op: str) -> bool:
        """Check if all occurrences of operator are within parentheses."""
        # Simple heuristic: check if expression has balanced parentheses around operator
        # This is a simplified version; a full parser would be more robust
        return False  # For now, assume not in parentheses

    def _split_by_operator(self, expr: str, operator: str, not_followed_by: str = '',
                           not_preceded_by: str = '') -> List[str]:
        """
        Split expression by operator, respecting parentheses.

        Only splits on operators at the top level (outside parentheses).

        Args:
            expr: Expression string
            operator: Operator to split by (e.g., '||', '&&', '>>')
            not_followed_by: If set, skip matches where the operator is immediately
                followed by this string (e.g., not_followed_by='>' for '>>' avoids '>>>')

        Returns:
            List of parts split by operator (returns single-element list if no split)
        """
        parts = []
        current = []
        paren_count = 0
        i = 0
        op_len = len(operator)

        while i < len(expr):
            if expr[i] == '(':
                paren_count += 1
                current.append(expr[i])
                i += 1
            elif expr[i] == ')':
                paren_count -= 1
                current.append(expr[i])
                i += 1
            elif paren_count == 0 and expr[i:i+op_len] == operator:
                if not_preceded_by and expr[max(0, i-len(not_preceded_by)):i] == not_preceded_by:
                    current.append(expr[i])
                    i += 1
                    continue
                # Check not_followed_by constraint (e.g., '>>' should not match '>>>')
                # Consume the entire extended token (operator + not_followed_by) so we
                # don't re-enter the loop at a position that makes the suffix look like
                # a fresh top-level match.
                if not_followed_by and expr[i+op_len:i+op_len+len(not_followed_by)] == not_followed_by:
                    skip_len = op_len + len(not_followed_by)
                    current.extend(list(expr[i:i+skip_len]))
                    i += skip_len
                    continue
                # Found operator at top level (outside parentheses)
                parts.append(''.join(current))
                current = []
                i += op_len
            else:
                current.append(expr[i])
                i += 1

        # Add the last part
        if current:
            parts.append(''.join(current))

        # Return single-element list if no split occurred
        return parts if len(parts) > 1 else [expr]

    def _extract_variables_from_expr(self, expr: str) -> set:
        """Extract variable names from an expression."""
        # Find all word tokens
        tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expr)

        # Filter out keywords (including instanceof which is a Java operator)
        keywords = {'true', 'false', 'null', 'none', 'this', 'super', 'return', 'new',
                   'if', 'while', 'for', 'int', 'long', 'float', 'double', 'boolean',
                   'char', 'void', 'final', 'is', 'True', 'False', 'after', 'block',
                   'instanceof'}

        # Filter out class names and field names in Class.field patterns
        # Find all Class.field or Class.FIELD patterns
        class_field_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        class_field_matches = re.findall(class_field_pattern, expr)
        excluded = set()
        for class_name, field_name in class_field_matches:
            excluded.add(class_name)  # Exclude class name
            excluded.add(field_name)  # Exclude static field name

        # Filter out tokens: keywords, excluded class/field names, and uppercase-starting
        # identifiers (Java class names by convention, not variable/parameter names)
        return {t for t in tokens
                if t not in keywords and t not in excluded and not t[0].isupper()}

    def format_solution(self, solution: Optional[Dict[str, Any]]) -> str:
        """
        Format the solution dictionary into a human-readable string.

        Args:
            solution: Dictionary mapping variable names to values

        Returns:
            Formatted string (e.g., "Example input: x=5, y=10")
        """
        if not solution:
            return ""

        param_strs = [f"{var}={val}" for var, val in sorted(solution.items())]
        return f"Please use the input: {', '.join(param_strs)}."

    def _path_needs_llm(self, path_nodes: List[Tuple]) -> bool:
        """
        Return True if the path contains conditions that Z3 cannot meaningfully solve.

        Triggers on any conditional node that has:
        - A method call or instanceof check
        - A null comparison
        - Any dot notation access: obj.field, this.x, a.length, Enum.CONSTANT
        - An array element access (e.g. src[srcPos])
        - A string or character literal
        - A boolean literal (true / false)
        - A ternary expression (? :)
        - A bare boolean variable with no comparison operator (e.g. if(flag), if(!flag))
        - An ALL_CAPS identifier not assigned anywhere in the path
          (treats it as an external constant/global Z3 cannot resolve)
        """
        # Pre-scan: collect variable names assigned in the path (non-branch nodes only)
        assigned_in_path: set = set()
        for node in path_nodes:
            if node[2] is not None:
                continue  # conditional node, not an assignment
            m = re.match(r'^\s*(?:[\w<>\[\]]+\s+)?(\w+)\s*[+\-*/%&|^]?=', node[1])
            if m:
                assigned_in_path.add(m.group(1))

        for node in path_nodes:
            statement = node[1]
            conditional = node[2]
            if conditional is None:
                continue  # not a branch, skip

            condition = self._extract_condition(statement)
            if condition is None:
                continue

            # Method call or instanceof
            if self._contains_method_call(condition):
                return True

            # Null comparison
            if re.search(r'\bnull\b', condition, re.IGNORECASE):
                return True

            # Any dot notation access: obj.field, this.x, a.length, Enum.CONSTANT
            # Z3 cannot model object state or field values
            if re.search(r'\b\w+\.\w+', condition):
                return True

            # Array element access (e.g. src[srcPos], arr[i+1])
            if re.search(r'\b\w+\s*\[', condition):
                return True

            # String or character literal
            if '"' in condition or "'" in condition:
                return True

            # Boolean literals — Z3 BitVec solver cannot represent true/false semantics
            if re.search(r'\b(true|false)\b', condition, re.IGNORECASE):
                return True

            # Ternary expression — Z3 does not parse ternary syntax
            if '?' in condition:
                return True

            # ALL_CAPS identifier not assigned in the path → external constant/global
            caps_refs = re.findall(r'\b([A-Z][A-Z0-9_]{2,})\b', condition)
            if any(v not in assigned_in_path for v in caps_refs):
                return True

            # Bare boolean variable — condition has no comparison operator,
            # meaning it is used directly as a boolean (e.g. if(flag), if(!isEmpty))
            stripped = re.sub(r'[!()\s]', '', condition)
            if stripped and re.match(r'^\w+$', stripped):
                return True

        return False

    def _render_llm_path_solving_prompt(self, path_conditions_str: str, method_name: str,
                                        source_file_numbered: str, source_file_name: str,
                                        previous_incorrect_answers: str = "",
                                        llm_verifier_response: str = "") -> Dict[str, str]:
        """Render the prompt for the LLM path solver."""
        from jinja2 import Environment, StrictUndefined
        from .config_loader import get_settings

        template = get_settings().llm_path_solving_prompt
        variables = {
            "source_file_name": source_file_name,
            "source_file_numbered": source_file_numbered,
            "method_name": method_name,
            "candidate_path": path_conditions_str,
            "previous_incorrect_answers": previous_incorrect_answers,
            "LLM_verifier_response": llm_verifier_response,
        }
        environment = Environment(undefined=StrictUndefined)
        return {
            "system": environment.from_string(template.system).render(variables),
            "user": environment.from_string(template.user).render(variables),
        }

    def _render_llm_verifier_prompt(self, path_conditions_str: str, method_name: str,
                                    source_file_numbered: str, source_file_name: str,
                                    input_statement: str) -> Dict[str, str]:
        """Render the prompt for the LLM verifier."""
        from jinja2 import Environment, StrictUndefined
        from .config_loader import get_settings

        template = get_settings().llm_verifier_prompt
        variables = {
            "source_file_name": source_file_name,
            "source_file_numbered": source_file_numbered,
            "method_name": method_name,
            "candidate_path": path_conditions_str,
            "input_statement": input_statement,
        }
        environment = Environment(undefined=StrictUndefined)
        return {
            "system": environment.from_string(template.system).render(variables),
            "user": environment.from_string(template.user).render(variables),
        }

    def _format_previous_llm_outputs(self, previous_outputs: List[str]) -> str:
        """Format previous rejected LLM answers for prompt reuse."""
        if not previous_outputs:
            return ""
        return "\n".join(
            f"Attempt {idx}: {output}"
            for idx, output in enumerate(previous_outputs, start=1)
        )

    def _format_previous_verifier_feedback(self, verifier_outputs: List[str]) -> str:
        """Format previous verifier feedback for prompt reuse."""
        if not verifier_outputs:
            return ""
        
        def _strip_no_prefix(output: str) -> str:
            return re.sub(r'^\s*no\s*[:,]?\s*', '', output.strip(), flags=re.IGNORECASE)

        return "\n".join(
            f"Attempt {idx}: {_strip_no_prefix(output)}"
            for idx, output in enumerate(verifier_outputs, start=1)
        )

    def _call_llm_solver(self, prompt: Dict[str, str], label: str) -> str:
        """Invoke the main path-solving LLM."""
        self.logger.debug(f"LLM path solving for method '{label}'")
        response, _, _ = self.llm_invoker.call_model(
            prompt,
            max_tokens=512,
            temperature=0.2,
        )
        # print(prompt)
        result = response.strip()
        self.logger.debug(f"LLM path solving output: {result}")
        return result

    def _call_llm_verifier(self, prompt: Dict[str, str], label: str) -> str:
        """Invoke the LLM verifier."""
        self.logger.debug(f"LLM verifier checking candidate input for method '{label}'")
        response, _, _ = self.llm_invoker.call_model(
            prompt,
            max_tokens=128,
            temperature=0.0,
        )
        # print(prompt)
        result = response.strip()
        # print(result)
        self.logger.debug(f"LLM verifier output: {result}")
        return result

    def _parse_llm_verifier_response(self, verifier_output: str) -> Optional[bool]:
        """Interpret the verifier output as Yes/No."""
        if not verifier_output:
            return None

        normalized = verifier_output.strip().lower()
        has_yes = re.search(r'\byes\b', normalized) is not None
        has_no = re.search(r'\bno\b', normalized) is not None

        if has_yes and not has_no:
            return True
        if has_no and not has_yes:
            return False
        return None

    def _verify_llm_solution(self, path_conditions_str: str, method_name: str,
                             source_file_numbered: str, source_file_name: str,
                             llm_response: str) -> Tuple[Optional[bool], str]:
        """Run the verifier LLM on a candidate path-solving response."""
        try:
            verifier_prompt = self._render_llm_verifier_prompt(
                path_conditions_str=path_conditions_str,
                method_name=method_name,
                source_file_numbered=source_file_numbered,
                source_file_name=source_file_name,
                input_statement=llm_response,
            )
            verifier_output = self._call_llm_verifier(verifier_prompt, method_name)
            verdict = self._parse_llm_verifier_response(verifier_output)
            if verdict is None:
                self.logger.warning(
                    f"LLM verifier returned an ambiguous answer for method '{method_name}': {verifier_output}"
                )
            return verdict, verifier_output
        except Exception as e:
            self.logger.warning(f"LLM verifier failed for method '{method_name}': {e}")
            return None, ""

    def _solve_path_with_llm(self, path_conditions_str: str, method_name: str,
                             source_file_numbered: str, source_file_name: str,
                             method_signature: str = "") -> str:
        """
        Use the LLM to find concrete inputs for a path with non-numerical conditions.

        Returns:
            The raw LLM response string, or "" on failure.
        """
        try:
            prompt_method_name = method_signature if method_signature else method_name
            label = prompt_method_name
            previous_outputs = []
            previous_verifier_outputs = []

            while True:
                solver_prompt = self._render_llm_path_solving_prompt(
                    path_conditions_str=path_conditions_str,
                    method_name=prompt_method_name,
                    source_file_numbered=source_file_numbered,
                    source_file_name=source_file_name,
                    previous_incorrect_answers=self._format_previous_llm_outputs(previous_outputs),
                    llm_verifier_response=self._format_previous_verifier_feedback(previous_verifier_outputs),
                )
                result = self._call_llm_solver(solver_prompt, label)
                if not result or "unsatisfiable" in result.lower():
                    return result

                if not self.enable_llm_verify:
                    return result

                verifier_result, verifier_output = self._verify_llm_solution(
                    path_conditions_str=path_conditions_str,
                    method_name=prompt_method_name,
                    source_file_numbered=source_file_numbered,
                    source_file_name=source_file_name,
                    llm_response=result,
                )
                if verifier_result is True:
                    return result

                previous_outputs.append(result)
                if verifier_output:
                    previous_verifier_outputs.append(verifier_output)
                if len(previous_outputs) >= self.llm_verify_max_rejections:
                    self.logger.info(
                        f"Skipping path for method '{label}' after "
                        f"{len(previous_outputs)} verifier rejections."
                    )
                    return ""

                self.logger.info(
                    f"Retrying LLM path solving for method '{label}' after verifier rejection "
                    f"({len(previous_outputs)}/{self.llm_verify_max_rejections})."
                )
        except Exception as e:
            self.logger.warning(f"LLM path solving failed for method '{method_name}': {e}")
            return ""

    def enhance_path_with_symbolic_execution(self, path_nodes: List[Tuple],
                                             path_conditions_str: str = "",
                                             method_name: str = "",
                                             method_signature: str = "",
                                             method_params: List[Dict] = None,
                                             source_file_numbered: str = "",
                                             source_file_name: str = "",
                                             force_llm: bool = False) -> Tuple[Optional[Dict], str]:
        """
        Enhance a path with symbolic execution results.

        If LLM path solving is enabled and the path contains non-numerical conditions
        (method calls, null checks, enum constants, etc.), the LLM is used instead of Z3.

        Args:
            path_nodes: List of path nodes from CFG
            path_conditions_str: Human-readable path string (used by LLM solver)
            method_name: Name of the method under test (used by LLM solver)
            source_file_numbered: Numbered source code (used by LLM solver)
            source_file_name: Source file name (used by LLM solver)

        Returns:
            Tuple of (solution dict or None, formatted string)
        """
        # Route to LLM solver when enabled and either explicitly requested or the
        # path has non-numerical conditions that Z3 cannot meaningfully solve.
        if (self.enable_llm_path_solving and self.llm_invoker
                and (force_llm or self._path_needs_llm(path_nodes))):
            llm_response = self._solve_path_with_llm(
                path_conditions_str, method_name, source_file_numbered, source_file_name,
                method_signature=method_signature,
            )
            if llm_response and "unsatisfiable" not in llm_response.lower():
                formatted = f"Please use the input: {llm_response}"
                # Return a non-None sentinel so prompt_builder includes this path
                return {"llm_result": llm_response}, formatted
            else:
                # LLM says unsatisfiable or failed — treat as no solution (skip path)
                return None, ""

        # Default: use Z3
        solution = self.solve_path_constraints(path_nodes, method_params=method_params)
        formatted = self.format_solution(solution)
        return solution, formatted
