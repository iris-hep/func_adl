import ast
from typing import Tuple, cast

import pytest_asyncio
from func_adl.ast.function_simplifier import make_args_unique


@pytest_asyncio.fixture(autouse=True)
def reset_ast_counters():
    import func_adl.ast.function_simplifier as fs
    fs.argument_var_counter = 0
    yield
    fs.argument_var_counter = 0


##############
# Test lambda copier
def util_run_parse(a_text: str) -> Tuple[ast.Lambda, ast.Lambda]:
    module = ast.parse(a_text)
    assert isinstance(module, ast.Module)
    s = cast(ast.Expr, module.body[0])
    a = s.value
    assert isinstance(a, ast.Lambda)
    new_a = make_args_unique(a)
    return (a, new_a)
