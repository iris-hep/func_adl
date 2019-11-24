# Some ast utils
import ast
from typing import Union, Optional, List, Any


def as_ast(p_var: Any) -> ast.AST:
    '''Convert any python constant into an ast

    Args:
        p_var   Some python variable that can be rendered with str(p_var)
                in a way the ast parse module will be able to ingest it.

    Returns:
        A python AST representing the object. For example, if a list is passed in, then
        the result will be an AST node of type ast.List.

    '''
    # If we are dealing with a string, we have to special case this.
    if isinstance(p_var, str):
        p_var = f"'{p_var}'"
    a = ast.parse(str(p_var))

    # Life out the thing inside the expression.
    return a.body[0].value


def function_call(function_name: str, args: List[ast.AST]) -> ast.AST:
    '''
    Generate a function call to `function_name` with a list of `args`.

    Args:
        function_name   String that is the function name
        args            List of ast's, each one is an argument.
    '''
    return ast.Call(ast.Name(function_name, ast.Load()),
                    args,
                    [])


# TODO: lambda_unwrap should only be used in the parse_ast code, no where else - we should be moving
# Lambda AST's around, not Module AST's.
def lambda_unwrap(l: ast.AST) -> ast.Lambda:
    '''Given an AST of a lambda node, return the lambda node. If it is burried in a module, then unwrap it first
    Python, when it parses an module, returns the lambda wrapped in a `Module` AST node. This gets rid of it, but
    is also flexible.

    Args:
        l:      Lambda AST. It may be wrapped in a module as well.

    Returns:
        `Lambda` AST node, regardless of how the `Lambda` was wrapped in `l`.

    Exceptions:
        If the AST node isn't a lambda or a module wrapping a lambda.
    '''
    lb = l.body[0].value if isinstance(l, ast.Module) else l
    if type(lb) is not ast.Lambda:
        raise BaseException('Attempt to get lambda expression body from {0}, which is not a lambda.'.format(type(l)))

    return lb


def lambda_args(l: Union[ast.Module, ast.Lambda]) -> ast.arguments:
    'Return the arguments of a lambda, no matter what form the lambda is in.'
    return lambda_unwrap(l).args


def lambda_body(l: Union[ast.Lambda, ast.Module]) -> ast.AST:
    '''
    Given an AST lambda node, get the expression it uses and return it. This just makes life easier,
    no real logic is occuring here.
    '''
    return lambda_unwrap(l).body


def lambda_call(args: Union[str, List[str]], l: ast.Lambda) -> ast.Call:
    '''
    Create a `Call` AST that calls a lambda with the named args.

    Args:
        args:       a single string or a list of strings, each string is an argument name to be passed in.
        l:          The lambda we want to call.

    Returns:
        A `Call` AST that calls the lambda with the given arguments.
    '''
    if isinstance(args, str):
        args = [args]
    named_args = [ast.Name(x, ast.Load()) for x in args]
    return ast.Call(lambda_unwrap(l), named_args, [])


def lambda_build(args: Union[str, List[str]], l_expr: ast.AST) -> ast.Lambda:
    '''
    Given a named argument(s), and an expression, build a `Lambda` AST node.

    Args:
        args:       the string names of the arguments to the lambda. May be a list or a single name
        l_expr:     An AST node that is the body of the lambda.

    Returns:
        The `Lambda` AST node.
    '''
    if type(args) is str:
        args = [args]

    ast_args = ast.arguments(args=[ast.arg(arg=x) for x in args])
    call_lambda = ast.Lambda(args=ast_args, body=l_expr)

    return call_lambda


def lambda_body_replace(l: ast.Lambda, new_expr: ast.AST) -> ast.Lambda:
    '''
    Return a new lambda function that has new_expr as the body rather than the old one. Otherwise, everything is the same.

    Args:
        l:          A ast.Lambda or ast.Module that points to a lambda.
        new_expr:   Expression that should replace this one.

    Returns:
        new_l: New lambda that looks just like the old one, other than the expression is new. If the old one was an ast.Module, so will this one be.
    '''
    if type(l) is not ast.Lambda:
        raise BaseException('Attempt to get lambda expression body from {0}, which is not a lambda.'.format(type(l)))

    new_l = ast.Lambda(l.args, new_expr)
    return new_l


def lambda_assure(east: ast.AST, nargs: Optional[int] = None):
    r'''
    Make sure the Python expression ast is a lambda call, and that it has the right number of args.

    Args:
        east:        python expression ast (module ast)
        nargs:      number of args it is required to have. If None, no check is done.
    '''
    if not lambda_test(east, nargs):
        raise BaseException(
            'Expression AST is not a lambda function with the right number of arguments')

    return east


def lambda_is_identity(l: ast.AST) -> bool:
    'Return true if this is a lambda with 1 argument that returns the argument'
    if not lambda_test(l, 1):
        return False

    b = lambda_unwrap(l)
    if not isinstance(b.body, ast.Name):
        return False

    a = b.args.args[0].arg
    return a == b.body.id


def lambda_is_true(l: ast.AST) -> bool:
    'Return true if this lambda always returns true'
    if not lambda_test(l):
        return False
    rl = lambda_unwrap(l)
    if not isinstance(rl.body, ast.NameConstant):
        return False

    return rl.body.value is True


def lambda_test(l: ast.AST, nargs: Optional[int] = None) -> bool:
    r''' Test arguments
    '''
    if not isinstance(l, ast.Lambda):
        if not isinstance(l, ast.Module):
            return False
        if len(l.body) != 1:
            return False
        if not isinstance(l.body[0], ast.Expr):
            return False
        if not isinstance(l.body[0].value, ast.Lambda):
            return False
    rl = lambda_unwrap(l) if type(l) is ast.Module else l
    if type(rl) is not ast.Lambda:
        return False
    if nargs is None:
        return True
    return len(lambda_unwrap(l).args.args) == nargs
