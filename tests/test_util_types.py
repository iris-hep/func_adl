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


def test_neg_float():
    assert follow_types(ast_lambda('lambda x: -1.5'), (int,)) == float


def test_any():
    assert follow_types(ast_lambda('lambda x: x'), (Any,)) == Any


def test_bool():
    assert follow_types(ast_lambda('lambda x: True'), (Any,)) == bool


def test_str():
    assert follow_types(ast_lambda('lambda x: "hi"'), (Any,)) == str


def test_add():
    assert follow_types(ast_lambda('lambda x: x + 1'), (int,)) == int


def test_add_float():
    assert follow_types(ast_lambda('lambda x: x + 1'), (float,)) == float


def test_sub():
    assert follow_types(ast_lambda('lambda x: x - 1'), (int,)) == int


def test_sub_float():
    assert follow_types(ast_lambda('lambda x: x - 1.1'), (int,)) == float


def test_mul():
    assert follow_types(ast_lambda('lambda x: x * 1'), (int,)) == int


def test_mul_float():
    assert follow_types(ast_lambda('lambda x: x * 1.1'), (int,)) == float


def test_div():
    assert follow_types(ast_lambda('lambda x: x / 1'), (int,)) == float


def test_class_method():
    class Jet:
        def pt(self) -> float:
            ...
    assert follow_types(ast_lambda('lambda x: x.pt()'), (Jet,)) == float


def test_class_bogus_method():
    class Jet:
        def pt(self) -> float:
            ...
    assert follow_types(ast_lambda('lambda x: x.ptt()'), (Jet,)) == Any


def test_class_unannotated_method():
    class Jet:
        def pt(self):
            ...
    assert follow_types(ast_lambda('lambda x: x.pt()'), (Jet,)) == Any
