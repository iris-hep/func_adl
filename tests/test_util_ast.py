import ast
import sys
from typing import Callable, cast

import pytest

from func_adl.util_ast import (
    _realign_indent,
    as_ast,
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


# Ast parsing
def test_as_ast_integer():
    if sys.version_info < (3, 8):
        assert "Num(n=1)" == ast.dump(as_ast(1))
    elif sys.version_info < (3, 9):
        assert "Constant(value=1, kind=None)" == ast.dump(as_ast(1))
    else:
        assert "Constant(value=1)" == ast.dump(as_ast(1))


def test_as_ast_string():
    if sys.version_info < (3, 8):
        assert "Str(s='hi there')" == ast.dump(as_ast("hi there"))
    elif sys.version_info < (3, 9):
        assert "Constant(value='hi there', kind=None)" == ast.dump(as_ast("hi there"))
    else:
        assert "Constant(value='hi there')" == ast.dump(as_ast("hi there"))


def test_as_ast_string_var():
    s = "hi there"
    if sys.version_info < (3, 8):
        assert "Str(s='hi there')" == ast.dump(as_ast(s))
    elif sys.version_info < (3, 9):
        assert "Constant(value='hi there', kind=None)" == ast.dump(as_ast(s))
    else:
        assert "Constant(value='hi there')" == ast.dump(as_ast(s))


def test_as_ast_list():
    if sys.version_info < (3, 8):
        assert "List(elts=[Str(s='one'), Str(s='two')], ctx=Load())" == ast.dump(
            as_ast(["one", "two"])
        )
    elif sys.version_info < (3, 9):
        assert (
            "List(elts=[Constant(value='one', kind=None), Constant(value='two', "
            "kind=None)], ctx=Load())" == ast.dump(as_ast(["one", "two"]))
        )
    else:
        assert "List(elts=[Constant(value='one'), Constant(value='two')], ctx=Load())" == ast.dump(
            as_ast(["one", "two"])
        )


# Fucntion Calling
def test_function_call_simple():
    a = function_call("dude", [as_ast(1)])
    print(ast.dump(ast.parse("dude(1)")))
    if sys.version_info < (3, 8):
        expected = "Call(func=Name(id='dude', ctx=Load()), args=[Num(n=1)], keywords=[])"
    elif sys.version_info < (3, 9):
        expected = (
            "Call(func=Name(id='dude', ctx=Load()), "
            "args=[Constant(value=1, kind=None)], keywords=[])"
        )
    else:
        expected = "Call(func=Name(id='dude', ctx=Load()), args=[Constant(value=1)], keywords=[])"
    assert expected == ast.dump(a)


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
    expr = ast.parse("x+1")
    ln = lambda_build("x", expr)
    assert isinstance(ln, ast.Lambda)


def test_lambda_build_list_arg():
    expr = ast.parse("x+1")
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
    if sys.version_info < (3, 8):
        assert "op=Add(), right=Num(n=1))" in a2_txt
    elif sys.version_info < (3, 9):
        assert "op=Add(), right=Constant(value=1, kind=None))" in a2_txt
    else:
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


def test_parse_nested_lambda():
    r = parse_as_ast(lambda x: (lambda y: y + 1)(x))
    assert isinstance(r, ast.Lambda)
    assert isinstance(r.body, ast.Call)


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


def test_parse_simple_func():
    "A oneline function defined at local scope"

    def doit(x):
        return x + 1

    f = parse_as_ast(doit)

    assert isinstance(f, ast.Lambda)
    assert len(f.args.args) == 1
    assert isinstance(f.body, ast.BinOp)


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

    def doit(x):
        ...

    f = parse_as_ast(lambda a: doit(a))  # type: ignore # NOQA
    assert "Name(id='doit'" in ast.dump(f)


def global_doit_non_func(x):
    ...


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
        def doit(self, x: int):
            ...

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
