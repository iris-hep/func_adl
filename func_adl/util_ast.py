from __future__ import annotations

import ast
import inspect
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

# Some functions to enable backwards compatibility.
# Capability may be degraded in older versions - particularly 3.6.
if sys.version_info >= (3, 8):  # pragma: no cover

    def as_literal(p: Union[str, int, float, bool, None]) -> ast.Constant:
        return ast.Constant(value=p, kind=None)

else:  # pragma: no cover

    def as_literal(p: Union[str, int, float, bool, None]):
        if isinstance(p, str):
            return ast.Str(p)
        elif isinstance(p, (int, float)):
            return ast.Num(p)
        elif isinstance(p, bool):
            return ast.NameConstant(p)
        elif p is None:
            return ast.NameConstant(None)
        else:
            raise ValueError(f"Unknown type {type(p)} - do not know how to make a literal!")


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
    """Given an AST of a lambda node, return the lambda node. If it is burried in a module, then
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
    easier, no real logic is occuring here.
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
    Return a new lambda function that has new_expr as the body rather than the old one. Otherwise,
    everything is the same.

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
            if not callable(v):
                return as_literal(self._lookup_dict[node.id])
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
    return "\n".join(stripped_lines)


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
        ast_source:     An AST or text string that represnets the lambda.
        caller_name:    The name of the function that the lambda is an arg to. If it
            is none, then it will attempt to scan the stack frame above to figure it out.

    Returns:
        An ast starting from the Lambda AST node.
    """
    if callable(ast_source):
        source = _realign_indent(inspect.getsource(ast_source))

        def find_next_lambda(method_name: str, source: str) -> Tuple[Optional[str], str]:
            "Find the lambda starting at the name"
            caller_idx = source.find(method_name)

            # If we couldn't find it, then we need to parse the whole thing.
            if caller_idx == -1:
                return None, source

            # If there is a newline, then we know this isn't the lambda
            # we want - it must start on the line we are given in the source.
            if "\n" in source[:caller_idx]:
                return None, ""

            source = source[caller_idx + len(method_name) :]

            i = 0
            open_count = 0
            while True:
                c = source[i]
                if c == "(":
                    open_count += 1
                elif c == ")":
                    open_count -= 1
                if open_count == 0:
                    break
                i += 1

            lambda_source = source[: i + 1]
            remaining_source = source[i + 1 :]

            return lambda_source, remaining_source

        # Look for the name of the calling function (e.g. 'Select' or 'Where', etc.) and
        # find all the instances on this line.
        if caller_name is None:
            caller_name = inspect.currentframe().f_back.f_code.co_name  # type: ignore

        found_lambdas: List[str] = []
        while True:
            lambda_source, remaining_source = find_next_lambda(caller_name, source)
            if lambda_source is None:
                break
            source = remaining_source
            found_lambdas.append(lambda_source)

        if len(found_lambdas) == 0:
            found_lambdas.append(source)

        # Parse them as a lambda function
        def parse(src: str) -> Optional[ast.Lambda]:
            while True:
                try:
                    a_module = ast.parse(src)
                    # If this is a function, not a lambda, then we can morph and return that.
                    if len(a_module.body) == 1 and isinstance(a_module.body[0], ast.FunctionDef):
                        lda = rewrite_func_as_lambda(a_module.body[0])  # type: ignore
                    else:
                        lda = next(
                            (node for node in ast.walk(a_module) if isinstance(node, ast.Lambda)),
                            None,
                        )

                    if lda is None:
                        raise ValueError(
                            f"Unable to recover source for function {ast_source} - '{src}'."
                        )
                    return lda
                except SyntaxError:
                    pass
                if src.endswith(")"):
                    src = src[:-1]
                else:
                    return None

        parsed_lambdas = [parse(src) for src in found_lambdas]

        # If we have more than one lambda, there are some tricks we can try - like argument names,
        # to see if they are different.
        src_ast: Optional[ast.Lambda] = None
        if len(found_lambdas) > 1:
            caller_arg_list = inspect.getfullargspec(ast_source).args
            for idx, p_lambda in enumerate(parsed_lambdas):
                lambda_args = [a.arg for a in p_lambda.args.args]  # type: ignore
                if lambda_args == caller_arg_list:
                    if src_ast is not None:
                        raise ValueError(
                            f"Found two calls to {caller_name} on same line - "
                            "split accross lines or change lambda argument names so they "
                            "are different."
                        )
                    src_ast = p_lambda
        else:
            assert len(found_lambdas) == 1
            src_ast = parsed_lambdas[0]

        if not src_ast:
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
