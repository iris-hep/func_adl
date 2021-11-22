import ast
from typing import Any
from func_adl.util_types import follow_types


def ast_lambda(lambda_func: str) -> ast.Lambda:
    'Return the ast starting from the Lambda node'
    return ast.parse(lambda_func).body[0].value  # type: ignore


def test_int():
    assert follow_types(ast_lambda('lambda x: 1'), (int,)) == int


def test_float():
    assert follow_types(ast_lambda('lambda x: 1.5'), (int,)) == float


def test_any():
    assert follow_types(ast_lambda('lambda x: x'), (Any,)) == Any


def test_bool():
    assert follow_types(ast_lambda('lambda x: True'), (Any,)) == bool


def test_str():
    assert follow_types(ast_lambda('lambda x: "hi"'), (Any,)) == str
