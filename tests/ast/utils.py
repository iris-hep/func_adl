import pytest

@pytest.fixture(autouse=True)
def reset_ast_counters():
    import func_adl.ast.function_simplifier as fs
    fs.argument_var_counter = 0
    yield
    fs.argument_var_counter = 0
