# Some ast utils
import ast
from typing import Any, List, Optional, Union, cast


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
    # assert isinstance(a.body[0], ast.Expr)
    b = a.body[0]
    assert isinstance(b, ast.Expr)
    return b.value


def function_call(function_name: str, args: List[ast.AST]) -> ast.Call:
    '''
    Generate a function call to `function_name` with a list of `args`.

    Args:
        function_name   String that is the function name
        args            List of ast's, each one is an argument.
    '''
    return ast.Call(ast.Name(function_name, ast.Load()),
                    args,
                    [])


def lambda_unwrap(lam: ast.AST) -> ast.Lambda:
    '''Given an AST of a lambda node, return the lambda node. If it is burried in a module, then unwrap it first
    Python, when it parses an module, returns the lambda wrapped in a `Module` AST node. This gets rid of it, but
    is also flexible.

    Args:
        lam:     Lambda AST. It may be wrapped in a module as well.

    Returns:
        `Lambda` AST node, regardless of how the `Lambda` was wrapped in `lam`.

    Exceptions:
        If the AST node isn't a lambda or a module wrapping a lambda.
    '''
    lb = cast(ast.Expr, lam.body[0]).value if isinstance(lam, ast.Module) else lam
    if not isinstance(lb, ast.Lambda):
        raise Exception('Attempt to get lambda expression body from {0}, which is not a lambda.'.format(type(lam)))

    return lb


def lambda_args(lam: Union[ast.Module, ast.Lambda]) -> ast.arguments:
    'Return the arguments of a lambda, no matter what form the lambda is in.'
    return lambda_unwrap(lam).args


def lambda_body(lam: Union[ast.Lambda, ast.Module]) -> ast.AST:
    '''
    Given an AST lambda node, get the expression it uses and return it. This just makes life easier,
    no real logic is occuring here.
    '''
    return lambda_unwrap(lam).body


def lambda_call(args: Union[str, List[str]], lam: Union[ast.Lambda, ast.Module]) -> ast.Call:
    '''
    Create a `Call` AST that calls a lambda with the named args.

    Args:
        args:       a single string or a list of strings, each string is an argument name to be passed in.
        lam:        The lambda we want to call.

    Returns:
        A `Call` AST that calls the lambda with the given arguments.
    '''
    if isinstance(args, str):
        args = [args]
    named_args = [ast.Name(x, ast.Load()) for x in args]
    return ast.Call(lambda_unwrap(lam), named_args, [])


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


def lambda_body_replace(lam: ast.Lambda, new_expr: ast.AST) -> ast.Lambda:
    '''
    Return a new lambda function that has new_expr as the body rather than the old one. Otherwise, everything is the same.

    Args:
        lam:        A ast.Lambda or ast.Module that points to a lambda.
        new_expr:   Expression that should replace this one.

    Returns:
        new_lam: New lambda that looks just like the old one, other than the expression is new. If the old one was an ast.Module, so will this one be.
    '''
    if type(lam) is not ast.Lambda:
        raise Exception('Attempt to get lambda expression body from {0}, which is not a lambda.'.format(type(lam)))

    new_lam = ast.Lambda(lam.args, new_expr)
    return new_lam


def lambda_assure(east: ast.AST, nargs: Optional[int] = None):
    r'''
    Make sure the Python expression ast is a lambda call, and that it has the right number of args.

    Args:
        east:        python expression ast (module ast)
        nargs:      number of args it is required to have. If None, no check is done.
    '''
    if not lambda_test(east, nargs):
        raise Exception(
            'Expression AST is not a lambda function with the right number of arguments')

    return east


def lambda_is_identity(lam: ast.AST) -> bool:
    'Return true if this is a lambda with 1 argument that returns the argument'
    if not lambda_test(lam, 1):
        return False

    b = lambda_unwrap(lam)
    if not isinstance(b.body, ast.Name):
        return False

    a1 = b.args.args[0].arg
    return a1 == b.body.id


def lambda_is_true(lam: ast.AST) -> bool:
    'Return true if this lambda always returns true'
    if not lambda_test(lam):
        return False
    rl = lambda_unwrap(lam)
    if not isinstance(rl.body, ast.NameConstant):
        return False

    return rl.body.value is True


def lambda_test(lam: ast.AST, nargs: Optional[int] = None) -> bool:
    r''' Test arguments
    '''
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


def parse_as_ast(ast_source: Union[str, ast.AST]) -> ast.Lambda:
    r'''Return an AST for a lambda function from several sources.

    We are handed one of several things:
        - An AST that is a lambda function
        - An AST that is a pointer to a Module that wraps an AST
        - Text that contains properly formatted ast code for a lambda function.

    In all cases, return a lambda function as an AST starting from the AST top node.

    Args:
        ast_source:     An AST or text string that represnets the lambda.

    Returns:
        An ast starting from the Lambda AST node.
    '''
    if isinstance(ast_source, str):
        a = ast.parse(ast_source.strip())
        return lambda_unwrap(a)
    else:
        return lambda_unwrap(ast_source)
