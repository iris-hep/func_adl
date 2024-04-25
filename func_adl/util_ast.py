from __future__ import annotations

import ast
import inspect
import sys
import tokenize
from collections import defaultdict
from types import ModuleType
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union, cast


def as_literal(p: Union[str, int, float, bool, None]) -> ast.Constant:
    """Convert a python constant into an AST constant node.

    Args:
        p (Union[str, int, float, bool, None]): what should be wrapped

    Returns:
        ast.Constant: The ast constant node that represents the value.
    """
    return ast.Constant(value=p, kind=None)


def as_ast(p_var: Any) -> ast.AST:
    """Convert any python constant into an ast

    Args:
        p_var   Some python variable that can be rendered with str(p_var)
                in a way the ast parse module will be able to ingest it.

    Returns:
        A python AST representing the object. For example, if a list is passed in, then
        the result will be an AST node of type ast.List.

    """
    # If we are dealing with a string, we have to special case this.
    if isinstance(p_var, str):
        p_var = f"'{p_var}'"
    a = ast.parse(str(p_var))

    # Life out the thing inside the expression.
    # assert isinstance(a.body[0], ast.Expr)
    b = a.body[0]
    assert isinstance(b, ast.Expr)
    return b.value


def function_call(function_name: str, args: List[ast.AST]) -> ast.Call:
    """
    Generate a function call to `function_name` with a list of `args`.

    Args:
        function_name   String that is the function name
        args            List of ast's, each one is an argument.
    """
    return ast.Call(ast.Name(function_name, ast.Load()), args, [])


def lambda_unwrap(lam: ast.AST) -> ast.Lambda:
    """Given an AST of a lambda node, return the lambda node. If it is buried in a module, then
    unwrap it first Python, when it parses an module, returns the lambda wrapped in a `Module` AST
    node. This gets rid of it, but is also flexible.

    Args:
        lam:     Lambda AST. It may be wrapped in a module as well.

    Returns:
        `Lambda` AST node, regardless of how the `Lambda` was wrapped in `lam`.

    Exceptions:
        If the AST node isn't a lambda or a module wrapping a lambda.
    """
    lb = cast(ast.Expr, lam.body[0]).value if isinstance(lam, ast.Module) else lam
    if not isinstance(lb, ast.Lambda):
        raise Exception(
            f"Attempt to get lambda expression body from {type(lam)}, " "which is not a lambda."
        )

    return lb


def lambda_args(lam: Union[ast.Module, ast.Lambda]) -> ast.arguments:
    "Return the arguments of a lambda, no matter what form the lambda is in."
    return lambda_unwrap(lam).args


def lambda_body(lam: Union[ast.Lambda, ast.Module]) -> ast.AST:
    """
    Given an AST lambda node, get the expression it uses and return it. This just makes life
    easier, no real logic is occurring here.
    """
    return lambda_unwrap(lam).body


def lambda_call(args: Union[str, List[str]], lam: Union[ast.Lambda, ast.Module]) -> ast.Call:
    """
    Create a `Call` AST that calls a lambda with the named args.

    Args:
        args:       a single string or a list of strings, each string is an argument name to be
                    passed in.
        lam:        The lambda we want to call.

    Returns:
        A `Call` AST that calls the lambda with the given arguments.
    """
    if isinstance(args, str):
        args = [args]
    named_args = [ast.Name(x, ast.Load()) for x in args]
    return ast.Call(lambda_unwrap(lam), named_args, [])


if sys.version_info >= (3, 9):

    def lambda_build(args: Union[str, List[str]], l_expr: ast.AST) -> ast.Lambda:
        """
        Given a named argument(s), and an expression, build a `Lambda` AST node.

        Args:
            args:       the string names of the arguments to the lambda. May be a list or a
                        single name
            l_expr:     An AST node that is the body of the lambda.

        Returns:
            The `Lambda` AST node.
        """
        if type(args) is str:
            args = [args]

        ast_args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=x) for x in args],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        )
        call_lambda = ast.Lambda(args=ast_args, body=l_expr)

        return call_lambda

elif sys.version_info >= (3, 8):  # pragma: no cover

    def lambda_build(args: Union[str, List[str]], l_expr: ast.AST) -> ast.Lambda:
        """
        Given a named argument(s), and an expression, build a `Lambda` AST node.

        Args:
            args:       the string names of the arguments to the lambda. May be a list or a
                        single name
            l_expr:     An AST node that is the body of the lambda.

        Returns:
            The `Lambda` AST node.
        """
        if type(args) is str:
            args = [args]

        ast_args = ast.arguments(
            posonlyargs=[],
            vararg=None,
            args=[ast.arg(arg=x, annotation=None, type_comment=None) for x in args],
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        call_lambda = ast.Lambda(args=ast_args, body=l_expr)

        return call_lambda

else:  # pragma: no cover

    def lambda_build(args: Union[str, List[str]], l_expr: ast.AST) -> ast.Lambda:
        """
        Given a named argument(s), and an expression, build a `Lambda` AST node.

        Args:
            args:       the string names of the arguments to the lambda. May be a list or a
                        single name
            l_expr:     An AST node that is the body of the lambda.

        Returns:
            The `Lambda` AST node.
        """
        if type(args) is str:
            args = [args]

        ast_args = ast.arguments(
            vararg=None,
            args=[ast.arg(arg=x, annotation=None) for x in args],
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        call_lambda = ast.Lambda(args=ast_args, body=l_expr)

        return call_lambda


def lambda_body_replace(lam: ast.Lambda, new_expr: ast.AST) -> ast.Lambda:
    """
    Return a new lambda function that has new_expr as the body rather than the old one.
    Otherwise, everything is the same.

    Args:
        lam:        A ast.Lambda or ast.Module that points to a lambda.
        new_expr:   Expression that should replace this one.

    Returns:
        new_lam: New lambda that looks just like the old one, other than the expression is new. If
        the old one was an ast.Module, so will this one be.
    """
    if type(lam) is not ast.Lambda:
        raise Exception(
            f"Attempt to get lambda expression body from {type(lam)}, " "which is not a lambda."
        )

    new_lam = ast.Lambda(lam.args, new_expr)
    return new_lam


def lambda_assure(east: ast.AST, nargs: Optional[int] = None):
    r"""
    Make sure the Python expression ast is a lambda call, and that it has the right number of args.

    Args:
        east:        python expression ast (module ast)
        nargs:      number of args it is required to have. If None, no check is done.
    """
    if not lambda_test(east, nargs):
        raise Exception(
            "Expression AST is not a lambda function with the right number of arguments"
        )

    return east


def lambda_is_identity(lam: ast.AST) -> bool:
    "Return true if this is a lambda with 1 argument that returns the argument"
    if not lambda_test(lam, 1):
        return False

    b = lambda_unwrap(lam)
    if not isinstance(b.body, ast.Name):
        return False

    a1 = b.args.args[0].arg
    return a1 == b.body.id


def lambda_is_true(lam: ast.AST) -> bool:
    "Return true if this lambda always returns true"
    if not lambda_test(lam):
        return False
    rl = lambda_unwrap(lam)
    if not isinstance(rl.body, ast.NameConstant):
        return False

    return rl.body.value is True


def lambda_test(lam: ast.AST, nargs: Optional[int] = None) -> bool:
    r"""Test arguments"""
    if not isinstance(lam, ast.Lambda):
        if not isinstance(lam, ast.Module):
            return False
        if len(lam.body) != 1:
            return False
        if not isinstance(lam.body[0], ast.Expr):
            return False
        if not isinstance(cast(ast.Expr, lam.body[0]).value, ast.Lambda):
            return False
    rl = lambda_unwrap(lam) if type(lam) is ast.Module else lam
    if type(rl) is not ast.Lambda:
        return False
    if nargs is None:
        return True
    return len(lambda_unwrap(lam).args.args) == nargs


def rewrite_func_as_lambda(f: ast.FunctionDef) -> ast.Lambda:
    """Rewrite a function definition as a lambda. The function can contain only
    a single return statement. ValueError is throw otherwise.

    Args:
        f (ast.FunctionDef): The ast pointing to the function definition.

    Raises:
        ValueError: An error occurred during the conversion:

    Returns:
        ast.Lambda: A lambda that is the equivalent.

    Notes:

        - It is assumed that the ast passed in won't be altered in place - no deep copy is
          done of the statement or args - they are just re-used.
    """
    if len(f.body) != 1:
        raise ValueError(
            f'Can handle simple functions of only one line - "{f.name}"' f" has {len(f.body)}."
        )
    if not isinstance(f.body[0], ast.Return):
        raise ValueError(
            f'Simple function must use return statement - "{f.name}" does ' "not seem to."
        )

    # the arguments
    args = f.args
    ret = cast(ast.Return, f.body[0])
    return ast.Lambda(args, ret.value)


class _rewrite_captured_vars(ast.NodeTransformer):
    def __init__(self, cv: inspect.ClosureVars):
        self._lookup_dict: Dict[str, Any] = dict(cv.nonlocals)
        self._lookup_dict.update(cv.globals)
        self._ignore_stack = []

    def visit_Name(self, node: ast.Name) -> Any:
        if self.is_arg(node.id):
            return node

        if node.id in self._lookup_dict:
            v = self._lookup_dict[node.id]
            if not callable(v) and not isinstance(v, ModuleType):
                # If it is something we know how to make into a literal, we just send it down
                # like that.
                return as_literal(v)
        return node

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        self._ignore_stack.append([a.arg for a in node.args.args])
        v = super().generic_visit(node)
        self._ignore_stack.pop()
        return v

    def is_arg(self, a_name: str) -> bool:
        "If the arg is on the stack, then return true"
        return any([a == a_name for frames in self._ignore_stack for a in frames])


def global_getclosurevars(f: Callable) -> inspect.ClosureVars:
    """Grab the closure over all passed function. Add all known global
    variables in as well.

    Args:
        f (Callable): The function pointer

    Returns:
        inspect.ClosureVars: Standard thing returned from `inspect.getclosurevars`,
            with the global variables added into it.
    """
    cv = inspect.getclosurevars(f)

    # Now, add all the globals that we might know about in case they are also
    # referenced inside this a nested lambda.
    cv.globals.update(f.__globals__)  # type: ignore

    return cv


def _realign_indent(s: str) -> str:
    """Move the first line to be at zero indent, and then apply same for everything
    below.

    Args:
        s (str): The string with indents

    Returns:
        str: Unindent string
    """
    lines = s.split("\n")
    spaces = len(lines[0]) - len(lines[0].lstrip())
    stripped_lines = [ln[spaces:] for ln in lines]
    while len(stripped_lines) > 0 and stripped_lines[-1].strip() == "":
        stripped_lines.pop()
    return "\n".join(stripped_lines)


def _get_sourcelines(f: Callable) -> Tuple[List[str], int]:
    """Get the source lines for a function, including a lambda, and make sure
    to return all the lines that might be important.

    TODO: WHen we hit Python 3.11, the better error return info might mean that tokens
    are better known and we can go back to the get source - and it will be a lot better.

    Args:
        f (Callable): The function

    Returns:
        List[str]: The source lines
    """
    lines, start_line = inspect.findsource(f)
    return lines, start_line


class _line_string_reader:
    def __init__(self, lines: List[str], initial_line: int):
        """Create a readline like interface for a list of strings.
        Uses the usual readline semantics, so that the cursor is
        always at the end of the string.

        Args:
            lines (List[str]): All the lines of the file
            initial_line (int): The next line to be read
        """
        self._lines = lines
        self._current_line = initial_line

    def readline(self) -> str:
        """Read the next line from the array. If we are off the
        end, return None

        Returns:
            Optional[str]: The next line in the file.
        """
        if self._current_line >= len(self._lines):
            return ""
        else:
            self._current_line += 1
            return self._lines[self._current_line - 1]


class _token_runner:
    def __init__(self, source: List[str], initial_line: int):
        """Track the tokenizer stream - burying a few details so higher level
        can work better.

        Args:
            source (List[str]): The source code
            initial_line (int): The initial line
        """
        self._source = source
        self._initial_line = initial_line

        self.init_tokenizer()

    def init_tokenizer(self):
        """Restart the tokenizer from the source and initial line"""
        self._tokenizer = tokenize.generate_tokens(
            _line_string_reader(self._source, self._initial_line).readline
        )

    def find_identifier(
        self, identifier: List[str], can_encounter_newline=True
    ) -> Tuple[Optional[tokenize.TokenInfo], Optional[tokenize.TokenInfo]]:
        """Find the next instance of the identifier. Return the token
        before it, and the identifier token.

        Args:
            identifier (str): The identifier to find
            can_encounter_newline (bool, optional): Can we encounter a newline. Defaults to True.

        Returns:
            Tuple[Optional[tokenize.TokenInfo], Optional[tokenize.TokenInfo]]: The tokens before
            and after the identifier. None if no `identifier` is found
        """
        last_identifier = None
        for t in self._tokenizer:
            if t.type == tokenize.NAME:
                if t.string in identifier:
                    return last_identifier, t
                last_identifier = t
            if t.type == tokenize.NEWLINE and not can_encounter_newline:
                break
        return None, None

    def tokens_till(
        self, stop_condition: Dict[int, List[str]]
    ) -> Generator[tokenize.Token, None, None]:  # type: ignore
        """Yield tokens until we find a stop condition.

        * Properly tracks parentheses, etc.

        Args:
            stop_condition (Dict[int, List[str]]): The token and string when we stop.
            can_encounter_newline (bool, optional): Can we encounter a newline. Defaults to True.

        Returns:
            Generator[tokenize.Token]: The tokens
        """
        # Keep track of the number of open parens, etc.
        parens = 0
        brackets = 0
        braces = 0

        for t in self._tokenizer:
            if (
                t.type in stop_condition
                and t.string in stop_condition[t.type]
                and parens == 0
                and brackets == 0
                and braces == 0
            ):
                return

            # Track things that could fool us
            if t.type == tokenize.OP:
                if t.string == "(":
                    parens += 1
                elif t.string == ")":
                    parens -= 1
                elif t.string == "[":
                    brackets += 1
                elif t.string == "]":
                    brackets -= 1
                elif t.string == "{":
                    braces += 1
                elif t.string == "}":
                    braces -= 1

            # Ignore comments
            if t.type == tokenize.COMMENT:
                continue

            yield t


def _get_lambda_in_stream(
    t_stream, start_token: tokenize.TokenInfo
) -> Tuple[Optional[ast.Lambda], bool]:
    """Finish of looking for a lambda in a token stream. Return the compiled
    (into an ast) lambda, and whether or not we saw a newline as we were parsing.

    Args:
        t_stream (generator): Tokenizer stream
        start_token (tokenize.TokenInfo): The starting lambda token

    Returns:
        Tuple[Optional[ast.Lambda], bool]: The compiled into an ast lambda, and whether or
        not we saw a newline
    """

    # Now, move forward until we find the end of the lambda expression.
    # We are expecting this lambda as part of a argument, so we are going to look
    # for a comma or a closing paren.
    accumulated_tokens = [start_token]
    saw_new_line = False
    for t in t_stream.tokens_till({tokenize.OP: [",", ")"]}):
        accumulated_tokens.append(t)
        if t.type == tokenize.NEWLINE or t.string == "\n":
            saw_new_line = True

    function_source = "(" + tokenize.untokenize(accumulated_tokens).lstrip() + ")"
    a_module = ast.parse(function_source)
    lda = next(
        (node for node in ast.walk(a_module) if isinstance(node, ast.Lambda)),
        None,
    )
    return lda, saw_new_line


def _parse_source_for_lambda(
    ast_source: Callable, caller_name: Optional[str] = None
) -> Optional[ast.Lambda]:
    """Use the python tokenizer to scan the source around `lambda_line`
    for a lambda. Turn that into an ast, and return it.

    Args:
        source (List[str]): Source code file
        lambda_line (int): Line in the source code where the `lambda` is seen.

    Returns:
        Optional[ast.Lambda]: The ast if a lambda is found.
    """
    # Find the start of the lambda or the separate 1-line function. We need to find the
    # enclosing function for the lambda - as funny things can be done with indents
    # and function arguments, and the tokenizer does not take kindly to surprising
    # "un-indents".
    func_name = None
    start_token = None
    source, lambda_line = _get_sourcelines(ast_source)
    t_stream = None
    while func_name is None:
        # Setup the tokenizer
        t_stream = _token_runner(source, lambda_line)

        func_name, start_token = t_stream.find_identifier(["def", "lambda"])

        if start_token is None:
            return None
        if start_token.string == "def":
            break
        if func_name is None:
            lambda_line -= 1

    assert start_token is not None
    assert t_stream is not None

    # If this is a function, then things are going to be very easy.
    if start_token.string == "def":
        function_source = _realign_indent(inspect.getsource(ast_source))
        a_module = ast.parse(function_source)
        lda = rewrite_func_as_lambda(a_module.body[0])  # type: ignore
    else:
        # Grab all the lambdas on a single line
        lambdas_on_a_line = defaultdict(list)
        saw_new_line = False
        while not saw_new_line:
            lda, saw_new_line = _get_lambda_in_stream(t_stream, start_token)
            lambdas_on_a_line[func_name.string if func_name is not None else None].append(lda)

            if saw_new_line:
                break

            func_name, start_token = t_stream.find_identifier(
                ["lambda"], can_encounter_newline=False
            )
            if start_token is None:
                break

        # Now lets make sure we pick up the right lambda. Do this by matching the caller
        # name (if we have it), and then by matching the arguments.

        lambdas_to_search = (
            lambdas_on_a_line[caller_name]
            if caller_name is not None
            else [ls for lambda_list in lambdas_on_a_line.values() for ls in lambda_list]
        )
        if len(lambdas_to_search) == 0:
            if caller_name is None:
                raise ValueError("Internal Error - Found no lambda!")
            else:
                raise ValueError(
                    f"Internal Error - Found no lambda in arguments to {caller_name}!"
                )

        def lambda_arg_list(lda: ast.Lambda) -> List[str]:
            return [a.arg for a in lda.args.args]

        caller_arg_list = inspect.getfullargspec(ast_source).args
        good_lambdas = [
            lda for lda in lambdas_to_search if lambda_arg_list(lda) == caller_arg_list
        ]
        if len(good_lambdas) == 0:
            raise ValueError(
                f"Internal Error - Found no lambda in source with the arguments {caller_arg_list}"
            )

        if len(good_lambdas) > 1:
            raise ValueError(
                "Found multiple calls on same line"
                + ("" if caller_name is None else f" for {caller_name}")
                + " - split the calls across "
                """lines or change lambda argument names so they are different. For example change:
                    df.Select(lambda x: x + 1).Select(lambda x: x + 2)
                    to:
                    df.Select(lambda x: x + 1).Select(lambda y: y + 2)
                """
            )

        lda = good_lambdas[0]

    return lda


def parse_as_ast(
    ast_source: Union[str, ast.AST, Callable], caller_name: Optional[str] = None
) -> ast.Lambda:
    r"""Return an AST for a lambda function from several sources.

    We are handed one of several things:
        - An AST that is a lambda function
        - An AST that is a pointer to a Module that wraps an AST
        - Text that contains properly formatted ast code for a lambda function.

    In all cases, return a lambda function as an AST starting from the AST top node.

    Args:
        ast_source:     An AST or text string that represents the lambda.
        caller_name:    The name of the function that the lambda is an arg to. If it
            is none, then it will attempt to scan the stack frame above to figure it
            out.

    Returns:
        An ast starting from the Lambda AST node.
    """
    if callable(ast_source):
        src_ast = _parse_source_for_lambda(ast_source, caller_name)
        if not src_ast:
            # This most often happens in a notebook when the lambda is defined in a funny place
            # and can't be recovered.
            raise ValueError(f"Unable to recover source for function {ast_source}.")

        # Since this is a function in python, we can look for lambda capture.
        call_args = global_getclosurevars(ast_source)
        return _rewrite_captured_vars(call_args).visit(src_ast)

    elif isinstance(ast_source, str):
        a = ast.parse(ast_source.strip())  # type: ignore
        return lambda_unwrap(a)

    else:
        assert isinstance(ast_source, ast.AST)
        return lambda_unwrap(ast_source)


def scan_for_metadata(a: ast.AST, callback: Callable[[ast.arg], None]):
    """Scan an ast for any MetaData function calls, and pass the metadata argument
    to the call back.
    """

    class metadata_finder(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            self.generic_visit(node)

            if isinstance(node.func, ast.Name) and node.func.id == "MetaData":
                callback(node.args[1])  # type: ignore

    metadata_finder().visit(a)


g_legal_capture_types = (str, int, float, bool, complex, str, bytes, ModuleType)


def check_ast(a: ast.AST):
    """Check to make sure the ast does not have anything we can't send over the wire
    in `qastle` or similar.

    Args:
        a (ast.AST): The AST to check

    Raises:
        ValueError: If something unsupported is found.
    """

    class ConstantTypeChecker(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant):
            if not isinstance(node.value, g_legal_capture_types):
                raise ValueError(f"Invalid constant type: {type(node.value)} for {ast.dump(node)}")
            self.generic_visit(node)

    # Usage example:
    checker = ConstantTypeChecker()
    checker.visit(a)
