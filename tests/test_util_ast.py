import ast
import sys
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from typing import Callable, cast

import pytest

from func_adl.util_ast import (
    _realign_indent,
    _resolve_called_lambdas,
    as_ast,
    check_ast,
    function_call,
    lambda_args,
    lambda_body_replace,
    lambda_build,
    lambda_call,
    lambda_is_identity,
    lambda_is_true,
    lambda_test,
    lambda_unwrap,
    parse_as_ast,
    rewrite_func_as_lambda,
    scan_for_metadata,
)
from tests.test_type_based_replacement import replace_name_with_constant


# Ast parsing
def test_as_ast_integer():
    assert "Constant(value=1)" == ast.dump(as_ast(1))


def test_as_ast_string():
    assert "Constant(value='hi there')" == ast.dump(as_ast("hi there"))


def test_as_ast_string_var():
    s = "hi there"
    assert "Constant(value='hi there')" == ast.dump(as_ast(s))


def test_as_ast_list():
    assert "List(elts=[Constant(value='one'), Constant(value='two')], ctx=Load())" == ast.dump(
        as_ast(["one", "two"])
    )


# Fucntion Calling
def test_function_call_simple():
    a = function_call("dude", [as_ast(1)])
    print(ast.dump(ast.parse("dude(1)")))
    expected = "Call(func=Name(id='dude', ctx=Load()), args=[Constant(value=1)], keywords=[])"


# Identity
def test_identity_is():
    assert lambda_is_identity(ast.parse("lambda x: x")) is True


def test_identity_isnot_body():
    assert lambda_is_identity(ast.parse("lambda x: x+1")) is False


def test_identity_isnot_args():
    assert lambda_is_identity(ast.parse("lambda x,y: x")) is False


def test_identity_isnot_body_var():
    assert lambda_is_identity(ast.parse("lambda x: x1")) is False


# Is this a lambda?
def test_lambda_test_expression():
    assert lambda_test(ast.parse("x")) is False


def test_lambda_assure_expression():
    try:
        lambda_test(ast.parse("x"))
        assert False
    except Exception:
        pass


def test_lambda_assure_lambda():
    try:
        lambda_test(ast.parse("lambda x : x+1"))
        assert False
    except Exception:
        pass


def test_lambda_args():
    args = lambda_args(ast.parse("lambda x: x+1"))
    assert len(args.args) == 1
    assert args.args[0].arg == "x"


def test_lambda_simple_ast_expr():
    assert lambda_test(ast.Not()) is False


def test_lambda_build_single_arg():
    expr = cast(ast.expr, ast.parse("x+1"))
    ln = lambda_build("x", expr)
    assert isinstance(ln, ast.Lambda)


def test_lambda_build_list_arg():
    expr = cast(ast.expr, ast.parse("x+1"))
    ln = lambda_build(["x"], expr)
    assert isinstance(ln, ast.Lambda)


def test_lambda_build_proper():
    "Make sure we are building the ast right for the version of python we are in"
    expr = ast.parse("x+1").body[0].value  # type: ignore
    ln = lambda_build("x", expr)
    assert ast.dump(ast.parse("lambda x: x+1").body[0].value) == ast.dump(ln)  # type: ignore


def test_call_wrap_list_arg():
    ln = ast.parse("lambda x: x+1")
    c = lambda_call(["x"], ln)
    assert isinstance(c, ast.Call)


def test_call_wrap_single_arg():
    ln = ast.parse("lambda x: x+1")
    c = lambda_call("x", ln)
    assert isinstance(c, ast.Call)


def test_lambda_test_lambda_module():
    assert lambda_test(ast.parse("lambda x: x")) is True


def test_lambda_test_raw_lambda():
    rl = cast(ast.Expr, ast.parse("lambda x: x").body[0]).value
    assert lambda_test(rl) is True


# Is this lambda always returning true?
def test_lambda_is_true_yes():
    assert lambda_is_true(ast.parse("lambda x: True")) is True


def test_lambda_is_true_no():
    assert lambda_is_true(ast.parse("lambda x: False")) is False


def test_lambda_is_true_expression():
    assert lambda_is_true(ast.parse("lambda x: x")) is False


def test_lambda_is_true_non_lambda():
    assert lambda_is_true(ast.parse("True")) is False


# Replacement
def test_lambda_replace_simple_expression():
    a1 = ast.parse("lambda x: x")

    nexpr = ast.parse("lambda y: y + 1")
    expr = lambda_unwrap(nexpr).body

    a2 = lambda_body_replace(lambda_unwrap(a1), expr)
    a2_txt = ast.dump(a2)
    assert "op=Add(), right=Constant(value=1))" in a2_txt


def test_rewrite_oneliner():
    a = ast.parse(
        """def oneline(a):
        return a+1"""
    )

    b = a.body[0]
    assert isinstance(b, ast.FunctionDef)
    ln = rewrite_func_as_lambda(b)

    assert isinstance(ln, ast.Lambda)
    assert len(ln.args.args) == 1
    assert ln.args.args[0].arg == "a"
    assert isinstance(ln.body, ast.BinOp)


def test_rewrite_twoliner():
    a = ast.parse(
        """def oneline(a):
        t = a+1
        return t"""
    )

    b = a.body[0]
    assert isinstance(b, ast.FunctionDef)
    with pytest.raises(ValueError) as e:
        rewrite_func_as_lambda(b)

    assert "simple" in str(e.value)


def test_rewrite_noret():
    a = ast.parse(
        """def oneline(a):
        a+1"""
    )

    b = a.body[0]
    assert isinstance(b, ast.FunctionDef)
    with pytest.raises(ValueError) as e:
        rewrite_func_as_lambda(b)

    assert "return" in str(e.value)


def test_resolve_called_lambdas():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: x + 1)(y)"))
    assert ast.unparse(r) == "y + 1"


def test_resolve_called_lambdas_arg_replacement():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: x + 1)(y+1)"))
    assert ast.unparse(r) == "y + 1 + 1"


def test_resolve_called_lambdas_same_arg():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: x + 1)(x)"))
    assert ast.unparse(r) == "x + 1"


def test_resolve_called_lambdas_nested1():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: (lambda x: x + 2)(x) + 1)(x)"))
    assert ast.unparse(r) == "x + 2 + 1"


def test_resolve_called_lambdas_nested2():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: (lambda x: x + 3)(x+2) + 4)(x+1)"))
    assert ast.unparse(r) == "x + 1 + 2 + 3 + 4"


def test_resolve_called_lambdas_captured():
    "Check simple lambda gets resolved"
    r = _resolve_called_lambdas().visit(ast.parse("(lambda x: (lambda y: x + y)(x+2) + 4)(x+1)"))
    # (lambda x: (lambda y: x + y)(x+2) + 4)(x+1)
    # (lambda y: x+1 + y)(x+1+2) + 4
    # x+1+x+1+2+4
    assert ast.unparse(r) == "x + 1 + (x + 1 + 2) + 4"


def test_parse_as_ast_lambda():
    ln = lambda_unwrap(ast.parse("lambda x: x + 1"))
    r = parse_as_ast(ln)
    assert isinstance(r, ast.Lambda)


def test_parse_as_str():
    r = parse_as_ast("lambda x: x + 1")
    assert isinstance(r, ast.Lambda)


def test_parse_as_callable_simple():
    r = parse_as_ast(lambda x: x + 1)
    assert isinstance(r, ast.Lambda)


def test_parse_lambda_capture():
    cut_value = 30
    r = parse_as_ast(lambda x: x > cut_value)
    r_true = parse_as_ast(lambda x: x > 30)
    assert ast.dump(r) == ast.dump(r_true)


def test_parse_lambda_capture_ignore_local():
    x = 30  # NOQA type: ignore
    r = parse_as_ast(lambda x: x > 20)
    r_true = parse_as_ast(lambda y: y > 20)
    assert ast.dump(r) == ast.dump(r_true).replace("'y'", "'x'")


g_cut_value = 30


def test_parse_lambda_capture_ignore_global():
    x = 30  # NOQA type: ignore
    r = parse_as_ast(lambda g_cut_value: g_cut_value > 20)
    r_true = parse_as_ast(lambda y: y > 20)
    assert ast.dump(r) == ast.dump(r_true).replace("'y'", "'g_cut_value'")


def test_parse_lambda_capture_nested_global():
    r = parse_as_ast(lambda x: (lambda y: y > g_cut_value)(x))
    r_true = parse_as_ast(lambda x: (lambda y: y > 30)(x))
    assert ast.dump(r) == ast.dump(r_true)


def test_parse_lambda_capture_nested_local():
    cut_value = 30
    r = parse_as_ast(lambda x: (lambda y: y > cut_value)(x))
    r_true = parse_as_ast(lambda x: (lambda y: y > 30)(x))
    assert ast.dump(r) == ast.dump(r_true)


def test_parse_lambda_class_constant():
    class forkit:
        it: int = 10

    r = parse_as_ast(lambda x: x > forkit.it)
    r_true = parse_as_ast(lambda x: x > 10)

    assert ast.unparse(r) == ast.unparse(r_true)


def test_parse_lambda_class_enum():

    class forkit:
        class MyEnum(Enum):
            VALUE = 20

    r = parse_as_ast(lambda x: x > forkit.MyEnum.VALUE)

    assert "VALUE" in ast.unparse(r)


def test_parse_lambda_with_implied_ns():
    "Test adding the special attribute to the module to prefix a namespace"
    # Add the attribute to the module
    global _object_cpp_as_py_namespace
    _object_cpp_as_py_namespace = "aweful"

    try:

        class forkit:
            class MyEnum(Enum):
                VALUE = 20

        r = parse_as_ast(lambda x: x > forkit.MyEnum.VALUE)

        assert "aweful.forkit.MyEnum.VALUE" in ast.unparse(r)

        found_it = False

        class check_it(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                nonlocal found_it
                if node.id == "aweful":
                    found_it = True
                    assert hasattr(node, "_ignore")
                    assert node._ignore  # type: ignore

        check_it().visit(r)
        assert found_it

    finally:
        # Remove the attribute from the module
        del _object_cpp_as_py_namespace


def test_parse_lambda_with_implied_ns_empty():
    "Test adding the special attribute to the module to prefix a namespace"
    # Add the attribute to the module
    global _object_cpp_as_py_namespace
    _object_cpp_as_py_namespace = ""

    try:

        class forkit:
            class MyEnum(Enum):
                VALUE = 20

        r = parse_as_ast(lambda x: x > forkit.MyEnum.VALUE)

        assert "forkit.MyEnum.VALUE" in ast.unparse(r)

        found_it = False

        class check_it(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                nonlocal found_it
                if node.id == "forkit":
                    found_it = True
                    assert hasattr(node, "_ignore")
                    assert node._ignore  # type: ignore

        check_it().visit(r)
        assert found_it

    finally:
        # Remove the attribute from the module
        del _object_cpp_as_py_namespace


def test_parse_lambda_class_constant_in_module():
    from . import xAOD

    r = parse_as_ast(lambda x: x > xAOD.my_fork_it.it)
    r_true = parse_as_ast(lambda x: x > 22)

    assert ast.unparse(r) == ast.unparse(r_true)


def test_parse_lambda_imported_class():
    "Check that numpy and similar are properly passed"

    import numpy as np

    r = parse_as_ast(lambda e: np.cos(e))
    assert "np.cos" in ast.unparse(r)


def test_parse_dataclass_reference():
    @dataclass
    class my_data_class:
        x: int

    r = parse_as_ast(lambda e: my_data_class(x=e))

    assert "<locals>.my_data_class" in ast.unparse(r)


def test_parse_named_tuple_reference():

    MyDataClass = namedtuple("MyDataClass", ["x"])

    r = parse_as_ast(lambda e: MyDataClass(x=e))

    assert "test_util_ast.MyDataClass" in ast.unparse(r)


def test_parse_simple_func():
    "A oneline function defined at local scope"

    def doit(x):
        return x + 1

    f = parse_as_ast(doit)

    assert isinstance(f, ast.Lambda)
    assert len(f.args.args) == 1
    assert isinstance(f.body, ast.BinOp)


def test_parse_simple_func_with_info():
    "A oneline function defined at local scope"

    def doit(x: int) -> int:
        "Add one to the arg"
        return x + 1

    f = parse_as_ast(doit)

    assert isinstance(f, ast.Lambda)
    assert len(f.args.args) == 1
    assert isinstance(f.body, ast.BinOp)


def test_parse_nested_func():
    "A oneline function defined at local scope"

    def func_1(x):
        return x + 1

    def func_2(x):
        return func_1(x) + 2

    f = parse_as_ast(func_2)

    assert ast.unparse(f) == "lambda x: x + 1 + 2"


def test_parse_nested_empty_func():
    "A oneline function defined at local scope"

    def func_1(x) -> int: ...

    def func_2(x) -> int:
        return func_1(x) + 2

    f = parse_as_ast(func_2)

    assert ast.unparse(f) == "lambda x: func_1(x) + 2"


def test_parse_nested_complex_func():
    "A oneline function defined at local scope"

    def func_1(x) -> int:
        if x > 10:
            return 5
        return 20

    def func_2(x) -> int:
        return func_1(x) + 2

    f = parse_as_ast(func_2)

    assert ast.unparse(f) == "lambda x: func_1(x) + 2"


def global_doit(x):
    return x + 1


def test_parse_global_simple_func():
    "A oneline function defined at global scope"

    f = parse_as_ast(global_doit)

    assert isinstance(f, ast.Lambda)
    assert len(f.args.args) == 1
    assert isinstance(f.body, ast.BinOp)


g_val = 50


def global_doit_capture(x):
    return x + g_val


def global_doit_capture_true(x):
    return x + 50


def test_parse_global_capture():
    "Global function, which includes variable capture"
    f = parse_as_ast(global_doit_capture)
    f_true = parse_as_ast(global_doit_capture_true)
    assert ast.dump(f) == ast.dump(f_true)


def test_unknown_function():
    "function that isn't declared"
    f = parse_as_ast(lambda a: unknown(a))  # type: ignore # NOQA
    assert "Name(id='unknown'" in ast.dump(f)


def test_known_local_function():
    "function that is declared locally"

    def doit(x): ...

    f = parse_as_ast(lambda a: doit(a))  # type: ignore # NOQA
    assert "Name(id='doit'" in ast.dump(f)


def global_doit_non_func(x): ...


def test_known_global_function():
    "function that is declared locally"

    f = parse_as_ast(lambda a: global_doit_non_func(a))  # type: ignore # NOQA
    assert "Name(id='global_doit_non_func'" in ast.dump(f)


def test_lambda_args_differentiation():
    "Use the arguments of the lambda to tell what we want"
    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    (my_obj().do_it(lambda x: x + 1).do_it(lambda y: y * 2))

    assert len(found) == 2
    l1, l2 = found
    assert isinstance(l1, ast.Lambda)
    assert isinstance(l1.body, ast.BinOp)
    assert isinstance(l1.body.op, ast.Add)

    assert isinstance(l2, ast.Lambda)
    assert isinstance(l2.body, ast.BinOp)
    assert isinstance(l2.body.op, ast.Mult)


def test_lambda_method_differentiation():
    "Use the method to tell what we want"
    found1 = []
    found2 = []

    class my_obj:
        def do_it1(self, x: Callable):
            found1.append(parse_as_ast(x, caller_name="do_it1"))
            return self

        def do_it2(self, x: Callable):
            found2.append(parse_as_ast(x, caller_name="do_it2"))
            return self

    (my_obj().do_it1(lambda x: x + 1).do_it2(lambda x: x * 2))

    assert len(found1) == 1
    assert len(found2) == 1

    l1 = found1[0]
    l2 = found2[0]

    assert isinstance(l1, ast.Lambda)
    assert isinstance(l1.body, ast.BinOp)
    assert isinstance(l1.body.op, ast.Add)

    assert isinstance(l2, ast.Lambda)
    assert isinstance(l2.body, ast.BinOp)
    assert isinstance(l2.body.op, ast.Mult)


# def test_parse_continues_accross_lines():
# NOTE: This test will fail because the python tokenizer will treat
# the continuation as a single line, and the parser will see these on
# the same line. This is how python works, and we should follow it.
#     "Use a line continuation and make sure we can tell the difference"
#     found = []

#     class my_obj:
#         def do_it(self, x: Callable):
#             found.append(parse_as_ast(x))
#             return self

#     # fmt: off
#     my_obj().do_it(lambda x: x + 1) \
#         .do_it(lambda x: x * 2)
#     # fmt: on

#     assert len(found) == 2
#     l1, l2 = found
#     assert isinstance(l1, ast.Lambda)
#     assert isinstance(l1.body, ast.BinOp)
#     assert isinstance(l1.body.op, ast.Add)

#     assert isinstance(l2, ast.Lambda)
#     assert isinstance(l2.body, ast.BinOp)
#     assert isinstance(l2.body.op, ast.Mult)


def test_decorator_parse():
    "More general case"

    seen_lambdas = []

    def dec_func(x: Callable):
        def make_it(y: Callable):
            return y

        seen_lambdas.append(parse_as_ast(x))
        return make_it

    @dec_func(lambda y: y + 2)
    def doit(x):
        return x + 1

    assert len(seen_lambdas) == 1
    l1 = seen_lambdas[0]
    assert isinstance(l1.body, ast.BinOp)
    assert isinstance(l1.body.op, ast.Add)


def test_indent_parse():
    "More general case"

    seen_funcs = []

    class h:
        @staticmethod
        def dec_func(x: Callable):
            def make_it(y: Callable):
                return y

            seen_funcs.append(x)
            return make_it

    class yo_baby:
        @h.dec_func(lambda y: y + 2)
        def doit(self, x: int): ...

    assert len(seen_funcs) == 1
    l1 = parse_as_ast(seen_funcs[0], "dec_func")
    assert isinstance(l1.body, ast.BinOp)
    assert isinstance(l1.body.op, ast.Add)


def test_two_deep_parse():
    "More general case"

    seen_lambdas = []

    def func_bottom(x: Callable):
        seen_lambdas.append(parse_as_ast(x))

    def func_top(x: Callable):
        func_bottom(x)

    func_top(lambda x: x + 1)

    assert len(seen_lambdas) == 1
    l1 = seen_lambdas[0]
    assert isinstance(l1.body, ast.BinOp)
    assert isinstance(l1.body.op, ast.Add)


def test_parse_continues_one_line():
    "Make sure we do not let our confusion confuse the user - bomb correctly here"
    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    with pytest.raises(Exception) as e:
        my_obj().do_it(lambda x: x + 1).do_it(lambda x: x * 2)

    assert "multiple" in str(e.value)


def test_parse_space_after_method():
    "Make sure we correctly parse a funnily formatted lambda"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it   (lambda x: x + 123)  # noqa: E211
    # fmt: on

    assert "123" in ast.dump(found[0])


def test_parse_multiline_bad_line_break():
    "Make sure we correctly parse a funnily formatted lambda"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(
        lambda x: x +  # noqa: W504
        123)
    # fmt: on

    assert "123" in ast.dump(found[0])


def test_parse_multiline_lambda_ok_with_one():
    "Make sure we can properly parse a multi-line lambda"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(
        lambda x: x
        + 1  # noqa: W503
        + 2  # noqa: W503
        + 20  # noqa: W503
    )
    # fmt: on

    assert "20" in ast.dump(found[0])


def test_parse_multiline_lambda_same_line():
    "Make sure we can properly parse a multi-line lambda"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(lambda x: x
                   + 1  # noqa: W503
                   + 2  # noqa: W503
                   + 20  # noqa: W503
                   )
    # fmt: on

    assert "20" in ast.dump(found[0])


def test_parse_multiline_lambda_ok_with_one_and_paran():
    "Make sure we can properly parse a multi-line lambda - using parens as delimiters"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(
        lambda x: (
            x
            + 1  # noqa: W503
            + 2  # noqa: W503
            + 20  # noqa: W503
        )
    )
    # fmt: on

    assert "20" in ast.dump(found[0])


def test_parse_multiline_lambda_blank_lines_no_infinite_loop():
    "Make sure we can properly parse a multi-line lambda - using parens as delimiters"

    found = []

    class my_obj:
        def Where(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

        def Select(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

        def AsAwkwardArray(self, stuff: str):
            return self

        def value(self):
            return self

    jets_pflow_name = "hi"
    ds_dijet = my_obj()

    # fmt: off
    jets_pflow = (
        ds_dijet.Select(lambda e: e.Jets(uncalibrated_collection=jets_pflow_name))
        .Select(lambda e: e.Where(lambda j: (j.pt() / 1000) > 30))
        .Select(lambda e: e.Select(lambda j: (j.pt() / 1000)))
        .AsAwkwardArray("JetPt")
        .value()
    )
    # fmt: on
    assert jets_pflow is not None  # Just to keep flake8 happy without adding a noqa above.
    assert "uncalibrated_collection" in ast.dump(found[0])


def test_parse_select_where():
    "Common lambas with different parent functions on one line - found in wild"

    found = []

    class my_obj:
        def Where(self, x: Callable):
            found.append(parse_as_ast(x, "Where"))
            return self

        def Select(self, x: Callable):
            found.append(parse_as_ast(x, "Select"))
            return self

        def AsAwkwardArray(self, stuff: str):
            return self

        def value(self):
            return self

    jets_pflow_name = "hi"
    ds_dijet = my_obj()

    # fmt: off
    jets_pflow = (
        ds_dijet.Select(lambda e: e.met).Where(lambda e: e > 100)
    )
    # fmt: on
    assert jets_pflow is not None  # Just to keep flake8 happy without adding a noqa above.
    assert "met" in ast.dump(found[0])


def test_parse_multiline_lambda_ok_with_one_as_arg():
    "Make sure we can properly parse a multi-line lambda - but now with argument"

    found = []

    class my_obj:
        def do_it(self, x: Callable, counter: int):
            found.append(parse_as_ast(x))
            assert counter > 0
            return self

    # fmt: off
    my_obj().do_it(
        lambda x: x
        + 1  # noqa: W503
        + 2  # noqa: W503
        + 20,  # noqa: W503
        50,
    )
    # fmt: on

    assert "20" in ast.dump(found[0])


def test_parse_multiline_lambda_with_funny_split():
    "This isn't on two lines but sort-of is - so we should parse it. See issue #84"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(lambda event: event + 1
                   ).do_it(lambda event: event)
    # fmt: on

    assert "Add()" in ast.dump(found[0])
    assert "Add()" not in ast.dump(found[1])


def test_parse_multiline_lambda_with_comment():
    "Comment in the middle of things"

    found = []

    class my_obj:
        def Where(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

        def Select(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

        def AsAwkwardArray(self, stuff: str):
            return self

        def value(self):
            return self

    source = my_obj()
    # fmt: off
    # flake8: noqa
    r = source.Where(lambda e:
        e.electron_pt.Where(lambda pT: pT > 25).Count() + e.muon_pt.Where(lambda pT: pT > 25).Count()== 1) \
        .Where(lambda e:\
            e.jet_pt.Where(lambda pT: pT > 25).Count() >= 4
        )     # noqa: E501
    # fmt: on

    assert "electron_pt" in ast.dump(found[0])


def test_parse_black_split_lambda_funny():
    "Seen in wild - formatting really did a number here"

    found = []

    class my_obj:
        def do_it(self, x: Callable):
            found.append(parse_as_ast(x))
            return self

    # fmt: off
    my_obj().do_it(
        lambda e: e.Jets("AntiKt4EMTopoJets").do_it(
            lambda j: j.Jets("AntiKt4EMTopoJets").do_it(
                lambda j1: j1.pt() / 1000.0
            )
        )
    )
    # fmt: on

    assert len(found) == 1
    assert "AntiKt4EMTopoJets" in ast.dump(found[0])


def test_parse_paramertized_function_simple():
    a = parse_as_ast(lambda e: e.jetAttribute["hi"](10))
    d_text = ast.dump(a)
    assert "Constant(value=10" in d_text
    assert "Constant(value='hi'" in d_text


def test_parse_parameterized_function_type():
    a = parse_as_ast(lambda e: e.jetAttribute[int](10))
    d_text = ast.dump(a)
    assert "Constant(value=10" in d_text

    # Needs to be updated...
    assert "Name(id='int'" in d_text


def test_parse_parameterized_function_defined_type():
    """This shows up in our calibration work - for example,

    `j.getValue[cpp_int]('decoration_name')
    """

    class my_type:
        bogus: int = 20

    a = parse_as_ast(lambda e: e.jetAttribute[my_type](10))
    d_text = ast.dump(a)
    assert "Constant(value=10" in d_text
    assert "<locals>.my_type" in d_text


def test_parse_parameterized_function_instance():
    class my_type:
        def __init__(self, n):
            self._n = n

    my_10 = my_type(10)

    a = parse_as_ast(lambda e: e.jetAttribute[my_10](10))
    d_text = ast.dump(a)
    assert "Constant(value=10" in d_text

    # Needs to be updated...
    assert (
        "Constant(value=<tests.test_util_ast.test_parse_parameterized_function_instance" in d_text
    )


def test_parse_metadata_there():
    recoreded = None

    def callback(a: ast.arg):
        nonlocal recoreded
        recoreded = a

    scan_for_metadata(ast.parse("MetaData(e, 22)"), callback)

    assert recoreded is not None
    assert 22 == ast.literal_eval(recoreded)


def test_realign_no_indent():
    assert _realign_indent("test") == "test"


def test_realign_indent_sp():
    assert _realign_indent("    test") == "test"


def test_realign_indent_tab():
    assert _realign_indent("\ttest") == "test"


def test_realign_indent_2lines():
    assert _realign_indent("    test()\n    dude()") == "test()\ndude()"


def test_realign_indent_2lines_uneven():
    assert _realign_indent("    test()\n        dude()") == "test()\n    dude()"


def test_check_ast_good():
    check_ast(ast.parse("1 + 2 + 'abc'"))


def test_check_ast_bad():
    class my_type:
        def __init__(self, n):
            self._n = n

    mt = my_type(10)
    a = ast.parse("1 + 2 + abc")
    a = replace_name_with_constant(a, "abc", mt)
    with pytest.raises(ValueError) as e:
        check_ast(a)

    assert "my_type" in str(e)


def test_Select_inline():
    "Make sure nothing funny happens to Select"
    r = parse_as_ast(lambda jets: jets.Select(lambda j: j.pt()))
    assert "function_call" not in ast.unparse(r)


def test_Range_inline():
    "Make sure nothing funny happens to Range"
    from func_adl import Range

    r = parse_as_ast(lambda jets: Range(1, 10).Select(lambda j: j + 1))
    assert "function_call" not in ast.unparse(r)


def test_parse_lambda_multiline_dictionary():
    """Multi-line lambda returning a dictionary should parse"""

    pdgid = 13

    found = []

    class my_obj:
        def Select(self, f: Callable):
            found.append(parse_as_ast(f))
            return self

    # fmt: off
    my_obj().Select(
        lambda e: e
    ).Select(
        lambda particles: {
            "good": particles.Where(lambda p: p.pdgId() == pdgid).Where(
                lambda p: p.hasDecayVtx()
            ),
            "none_count": particles.Where(lambda p: p.pdgId() == pdgid)
            .Where(lambda p: not p.hasDecayVtx())
            .Count(),
        }
    )
    # fmt: on

    assert isinstance(found[0], ast.Lambda)
