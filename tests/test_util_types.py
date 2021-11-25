import ast
from typing import Any
from func_adl.util_types import follow_types


def ast_lambda(lambda_func: str) -> ast.Lambda:
    'Return the ast starting from the Lambda node'
    return ast.parse(lambda_func).body[0].value  # type: ignore

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
