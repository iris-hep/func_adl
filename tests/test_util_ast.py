import ast
from typing import Callable, cast

import pytest

from func_adl.util_ast import (
    as_ast, function_call, lambda_args, lambda_body_replace, lambda_build,
    lambda_call, lambda_is_identity, lambda_is_true, lambda_test,
    lambda_unwrap, parse_as_ast)


# Ast parsing
def test_as_ast_integer():
    assert "Num(n=1)" == ast.dump(as_ast(1))

def test_as_ast_string():
    assert "Str(s='hi there')" == ast.dump(as_ast("hi there"))

def test_as_ast_string_var():
    s = "hi there"
    assert "Str(s='hi there')" == ast.dump(as_ast(s))

def test_as_ast_list():
    assert "List(elts=[Str(s='one'), Str(s='two')], ctx=Load())" == ast.dump(as_ast(["one", "two"]))

# Fucntion Calling
def test_function_call_simple():
    a = function_call('dude', [as_ast(1)])
    print (ast.dump(ast.parse('dude(1)')))
    expected = "Call(func=Name(id='dude', ctx=Load()), args=[Num(n=1)], keywords=[])"
    assert expected == ast.dump(a)

# Identity
def test_identity_is():
    assert lambda_is_identity(ast.parse('lambda x: x')) == True

def test_identity_isnot_body():
    assert lambda_is_identity(ast.parse('lambda x: x+1')) == False

def test_identity_isnot_args():
    assert lambda_is_identity(ast.parse('lambda x,y: x')) == False

def test_identity_isnot_body_var():
    assert lambda_is_identity(ast.parse('lambda x: x1')) == False

# Is this a lambda?
def test_lambda_test_expression():
    assert lambda_test(ast.parse("x")) == False

def test_lambda_assure_expression():
    try:
        lambda_test(ast.parse("x"))
        assert False
    except:
        pass

def test_lambda_assure_lambda():
    try:
        lambda_test(ast.parse("lambda x : x+1"))
        assert False
    except:
        pass

def test_lambda_args():
    args = lambda_args(ast.parse("lambda x: x+1"))
    assert len(args.args)==1
    assert args.args[0].arg == 'x'

def test_lambda_simple_ast_expr():
    assert lambda_test(ast.Not()) == False

def test_lambda_build_single_arg():
    expr = ast.parse("x+1")
    l = lambda_build("x", expr)
    assert isinstance(l, ast.Lambda)

def test_lambda_build_list_arg():
    expr = ast.parse("x+1")
    l = lambda_build(["x"], expr)
    assert isinstance(l, ast.Lambda)

def test_call_wrap_list_arg():
    l = ast.parse('lambda x: x+1')
    c = lambda_call(['x'], l)
    assert isinstance(c, ast.Call)

def test_call_wrap_single_arg():
    l = ast.parse('lambda x: x+1')
    c = lambda_call('x', l)
    assert isinstance(c, ast.Call)

def test_lambda_test_lambda_module():
    assert lambda_test(ast.parse('lambda x: x')) == True

def test_lambda_test_raw_lambda():
    rl = cast(ast.Expr, ast.parse('lambda x: x').body[0]).value
    assert lambda_test(rl) == True

# Is this lambda always returning true?
def test_lambda_is_true_yes():
    assert lambda_is_true(ast.parse("lambda x: True")) == True

def test_lambda_is_true_no():
    assert lambda_is_true(ast.parse("lambda x: False")) == False

def test_lambda_is_true_expression():
    assert lambda_is_true(ast.parse("lambda x: x")) == False

def test_lambda_is_true_non_lambda():
    assert lambda_is_true(ast.parse("True")) == False

# Replacement
def test_lambda_replace_simple_expression():
    a1 = ast.parse("lambda x: x")

    nexpr = ast.parse("lambda y: y + 1")
    expr = lambda_unwrap(nexpr).body

    a2 = lambda_body_replace(lambda_unwrap(a1), expr)
    a2_txt = ast.dump(a2)
    assert "op=Add(), right=Num(n=1))" in a2_txt


def test_parse_as_ast_lambda():
    l = lambda_unwrap(ast.parse("lambda x: x + 1"))
    r = parse_as_ast(l)
    assert isinstance(r, ast.Lambda)


def test_parse_as_str():
    r = parse_as_ast('lambda x: x + 1')
    assert isinstance(r, ast.Lambda)


def test_parse_as_callable_simple():
    r = parse_as_ast(lambda x: x + 1)
    assert isinstance(r, ast.Lambda)


def test_parse_nested_lambda():
    r = parse_as_ast(lambda x: (lambda y: y + 1)(x))
    assert isinstance(r, ast.Lambda)

def test_parse_two_lambdas():
    with pytest.raises(Exception) as e:
        (parse_as_ast(lambda x: x + 1), parse_as_ast(lambda y: y * 10))

    assert 'While parsing' in str(e.value)


def test_parse_simple_func():
    'Fail if we get a function - one day we can do this, but not quite yet'
    def doit(x):
        return x + 1

    with pytest.raises(Exception):
        parse_as_ast(doit)


def test_run_on_parse():
    'Emulate the syntax you often find when you have a multistep query'
    class my_obj:
        def do_it(self, x: Callable):
            parse_as_ast(x)
            return self

    # #&$&#^$^@ this parse error makes this almost not useful.
    with pytest.raises(Exception):
        long_expr = my_obj() \
            .do_it(lambda x: x + 1) \
            .do_it(lambda y: y + 2)
